from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Mapping as ABCMapping
from typing import Any


def _resolve_ref(schema: Mapping[str, Any], ref: str) -> Mapping[str, Any] | None:
    """Resolve local JSON Schema $refs like '#/$defs/Name'."""
    if not ref.startswith("#/"):
        return None

    node: Mapping[str, Any] | None = schema
    for part in ref[2:].split("/"):
        # node may be None; get() returns Any | None
        next_node = None if node is None else node.get(part)
        if not isinstance(next_node, ABCMapping):
            return None
        # after isinstance, mypy narrows next_node to Mapping[Any, Any]
        node = next_node

    return node


def _extract_choices(schema: Mapping[str, Any], node: Any) -> list[str] | None:
    """
    Extract enum values from a schema node, handling:
    - inline 'enum'
    - direct '$ref'
    - composition via 'allOf'/'anyOf'/'oneOf' that contain refs or enums
    """
    if not isinstance(node, ABCMapping):
        return None

    # inline enum
    enum = node.get("enum")
    if isinstance(enum, list) and enum:
        return [str(v) for v in enum]

    # direct $ref
    ref = node.get("$ref")
    if isinstance(ref, str):
        ref_schema = _resolve_ref(schema, ref)
        if isinstance(ref_schema, ABCMapping):
            ref_enum = ref_schema.get("enum")
            if isinstance(ref_enum, list) and ref_enum:
                return [str(v) for v in ref_enum]

    # composition wrappers
    for key in ("allOf", "anyOf", "oneOf"):
        subs = node.get(key)
        if isinstance(subs, list):
            for sub in subs:
                values = _extract_choices(schema, sub)
                if values:
                    return values

    return None


def _extract_type(schema: Mapping[str, Any], node: Any) -> str | None:
    """
    Extract the type from a schema node, handling:
    - inline 'type'
    - direct '$ref' (resolves to 'object' for model refs)
    - composition via 'allOf'/'anyOf'/'oneOf'

    Returns:
        str: Type like "string", "integer", "number", "boolean", "array", "object", or None
    """
    if not isinstance(node, ABCMapping):
        return None

    # inline type
    node_type = node.get("type")
    if isinstance(node_type, str):
        return node_type

    # direct $ref
    ref = node.get("$ref")
    if isinstance(ref, str):
        ref_schema = _resolve_ref(schema, ref)
        if isinstance(ref_schema, ABCMapping):
            ref_type = ref_schema.get("type")
            if isinstance(ref_type, str):
                return ref_type

    # composition wrappers
    for key in ("allOf", "anyOf", "oneOf"):
        subs = node.get(key)
        if isinstance(subs, list):
            for sub in subs:
                sub_type = _extract_type(schema, sub)
                if sub_type:
                    return sub_type

    return None


def _pick_preferred_branch(node: Any, root_schema: Mapping[str, Any]) -> Any:
    """
    If node is a union (anyOf/oneOf), pick a representative branch for *display* and
    recursion. We prefer a non-null branch so Optional[T] becomes describable as T.
    If there is no clear non-null branch, return the node unchanged.
    """
    if not isinstance(node, ABCMapping):
        return node
    for key in ("anyOf", "oneOf"):
        subs = node.get(key)
        if isinstance(subs, list) and subs:
            for sub in subs:
                t = _extract_type(root_schema, sub)
                if t and t != "null":
                    return sub
            return subs[0]
    return node


def build_schema_description(
    schema: Mapping[str, Any],
    header: str | None = "Feldhinweise und erlaubte Werte (getrennt durch Semikolons):",
    type_description_prefix: str | None = "Beschreibung: ",
    cardinality_prefix: str | None = "Kardinalität: ",
    type_prefix: str | None = "Typ: ",
    choices_prefix: str | None = "Zulässige Werte: ",
    component_separator: str = " | ",
    choices_separator: str = "; ",
    indent_step: str = "  ",
    include_field_descriptions: bool = True,
    include_type_descriptions: bool = True,
    # internal args
    indent: int = 0,
    root_schema: Mapping[str, Any] | None = None,
) -> str:
    """
    Build a human‑readable summary for a JSON Schema.

    Output format:
    - Optional first line: "<type_description_prefix><schema.description>" if include_type_descriptions and the description exists
    - Optional header line (only at top level if header is not None)
    - One line per property with format depending on which prefix parameters are not None:
      "<indent>- <name>[: <description>][<separator><cardinality_prefix><cardinality>][<separator><type_prefix><type>][<separator><enum_prefix><values>]"
    - For nested objects, recursively includes their properties with increased indentation

    Cardinality rules:
    - type=array ⇒ "0..*"
    - non-array with "default" ⇒ "0..1"
    - non-array without "default" ⇒ "1"

    Type extraction:
    - Supports inline "type", direct "$ref", and compositions via "allOf"/"anyOf"/"oneOf"
    - For arrays, type is taken from "items"

    Choices extraction:
    - Supports inline enums, direct "$ref", and compositions via "allOf"/"anyOf"/"oneOf"
    - For arrays, choices are taken from "items" (including "$ref" or compositions)

    Args:
        schema: The JSON Schema dictionary to process
        header: Header text for field list (only shown at top level, None to omit)
        type_description_prefix: Prefix for type descriptions (descriptions for the overall schema and nested schemas, not field descriptions)
        cardinality_prefix: Prefix for cardinality information (None to omit cardinality)
        type_prefix: Prefix for type information (None to omit types)
        choices_prefix: Prefix for choices value lists (None to omit choices)
        component_separator: Separator between field components (name, cardinality, type, choices)
        choices_separator: Separator between individual choices values
        indent_step: String used for each indentation level
        include_field_descriptions: Whether to include field/property descriptions in the output
        include_type_descriptions: Whether to include schema/type descriptions (top-level and nested) in the output
        indent: Current indentation level (internal, for recursion)
        root_schema: Root schema containing $defs (internal, for recursion)

    Returns:
        Multi-line string summarizing schema structure, fields, and constraints
    """
    if root_schema is None:
        root_schema = schema

    lines = []
    prefix = indent_step * indent

    # Add description
    if include_type_descriptions is not None:
        schema_desc = schema.get("description", "")
        if schema_desc:
            # remove all newlines and extra spaces from the description
            schema_desc = " ".join(schema_desc.split())
            lines.append(f"{prefix}{type_description_prefix or ""}{schema_desc}")

    if header:
        lines.append(header)

    props = schema.get("properties", {}) or {}
    for name, spec in props.items():
        # Single check for array vs non-array handling
        is_array = spec.get("type") == "array"
        target = spec.get("items") if is_array else spec
        target_for_hints = _pick_preferred_branch(target, root_schema)

        # Determine cardinality
        has_default = "default" in spec
        cardinality = "0..*" if is_array else ("0..1" if has_default else "1")

        # Extract type and choices from target
        field_type = _extract_type(root_schema, target_for_hints)
        choices = _extract_choices(root_schema, target_for_hints)

        # Build field line
        hint = f"{prefix}- {name}:"
        # the field description is mandatory (if exists)
        if include_field_descriptions:
            desc = spec.get("description", "")
            # remove all newlines and extra spaces from the description
            desc = " ".join(desc.split())
            if desc:
                hint += f" {desc}"
        if cardinality_prefix is not None:
            hint += f"{component_separator}{cardinality_prefix}{cardinality}"
        if field_type and type_prefix is not None:
            hint += f"{component_separator}{type_prefix}{field_type}"
        if choices and choices_prefix is not None:
            hint += f"{component_separator}{choices_prefix}" + choices_separator.join(choices)

        lines.append(hint)

        # Handle nested objects recursively:
        # - $ref objects
        # - inline object schemas with "properties" (needed for metadata wrappers)
        if field_type == "object" and isinstance(target_for_hints, ABCMapping):
            nested_schema: Mapping[str, Any] | None = None

            ref = target_for_hints.get("$ref")
            if isinstance(ref, str):
                nested_schema = _resolve_ref(root_schema, ref)
            elif isinstance(target_for_hints.get("properties"), ABCMapping):
                nested_schema = target_for_hints

            if nested_schema:
                nested_content = build_schema_description(
                    nested_schema,
                    indent=indent + 1,
                    root_schema=root_schema,
                    # no header for nested
                    header=None,
                    type_description_prefix=type_description_prefix,
                    cardinality_prefix=cardinality_prefix,
                    type_prefix=type_prefix,
                    choices_prefix=choices_prefix,
                    component_separator=component_separator,
                    choices_separator=choices_separator,
                    indent_step=indent_step,
                    include_field_descriptions=include_field_descriptions,
                    include_type_descriptions=include_type_descriptions,
                )
                lines.append(nested_content)

    return "\n".join(lines)


METADATA_SCHEMA_WITH_EVIDENCE: dict[str, Any] = {
    "type": "object",
    "properties": {
        "evidence_anchor": {
            "type": "string",
            "description": "Verbatim excerpt from the source text supporting the extracted content.",
        }
    },
    "required": ["evidence_anchor"],
    "additionalProperties": False,
}
# the above produces the same result as using this:
METADATA_SCHEMA_WITH_EVIDENCE_SHORTHAND: dict[str, Any] = {
    "evidence_anchor": {
        "type": "string",
        "description": "Verbatim excerpt from the source text supporting the extracted content.",
    }
}


def _is_objectish(node: Mapping[str, Any]) -> bool:
    node_type = node.get("type")
    if node_type == "object":
        return True
    return isinstance(node.get("properties"), ABCMapping) or "patternProperties" in node


def _is_arrayish(node: Mapping[str, Any]) -> bool:
    node_type = node.get("type")
    if node_type == "array":
        return True
    return "items" in node or "prefixItems" in node


def _schema_should_be_wrapped(
    root: Mapping[str, Any],
    node: Any,
    *,
    _ref_stack: set[str] | None = None,
) -> bool:
    """
    Decide whether a schema node should be replaced by the metadata wrapper produced by
    `wrap_terminals_with_metadata()`.

    Intuition
    ---------
    The wrapper is meant for "leaf-like" value schemas (e.g., string/integer/enum/const) so
    the model can return both the extracted value (`content`) and its metadata
    (e.g., `evidence_anchor`). We therefore wrap *value* nodes, not structural nodes.

    What counts as "should be wrapped"
    ----------------------------------
    Returns True if `node` represents a *non-null* scalar value schema, an enum, or a
    non-null const --- including the case where `node` is a `$ref` that resolves to such
    a schema.

    Examples that return True:
      - {"type": "string"}
      - {"type": "integer"}
      - {"enum": ["A", "B"], "type": "string"}
      - {"const": 123}
      - {"$ref": "#/$defs/HabitatEnum"}  (if that $defs entry is an enum / scalar schema)

    What does NOT get wrapped (and why)
    -----------------------------------
    - Objects and arrays are not wrapped because they are structural containers; their
      *children* (properties/items) are processed recursively instead.
    - Unions/compositions (anyOf/oneOf/allOf) are not wrapped at the union root if they
      include `null` or a structural branch. This is intentional:
        * For Optional[T] patterns (e.g., anyOf: [T, null]) we want the overall field to
          remain nullable, while only the non-null branch `T` receives metadata.
          Wrapping the union root would allow invalid combinations like
          {"content": null, "evidence_anchor": "..."}.
        * For unions like "string OR object", only the scalar branch should become a
          wrapper, while the object branch remains an object whose leaf fields are wrapped.
    - `const: null` is treated as non-wrappable for the same reason as nullable unions:
      it would again allow metadata without actual content.

    Implementation notes
    --------------------
    The function resolves local JSON Schema `$ref`s using `root` and uses `_ref_stack`
    for cycle protection.
    """

    if not isinstance(node, ABCMapping):
        return False

    if _is_objectish(node) or _is_arrayish(node):
        return False

    scalar_types = {"string", "number", "integer", "boolean"}

    # direct scalar type
    node_type = node.get("type")
    if isinstance(node_type, str):
        if node_type in scalar_types:
            return True
        if node_type in {"object", "array", "null"}:
            return False
    elif isinstance(node_type, list):
        if node_type and all(isinstance(t, str) and t in scalar_types for t in node_type):
            return True

    # enum/const
    if "const" in node and node.get("const") is None:
        return False

    if "enum" in node or "const" in node:
        return True

    # $ref
    ref = node.get("$ref")
    if isinstance(ref, str):
        target = _resolve_ref(root, ref)
        if not isinstance(target, ABCMapping):
            return False
        if _ref_stack is None:
            _ref_stack = set()
        if ref in _ref_stack:
            return False  # cycle safety
        _ref_stack.add(ref)
        return _schema_should_be_wrapped(
            root,
            target,
            _ref_stack=_ref_stack,
        )

    # anyOf / oneOf: terminal only if all branches are terminal
    for key in ("anyOf", "oneOf"):
        subs = node.get(key)
        if isinstance(subs, list) and subs:
            return all(_schema_should_be_wrapped(root, s, _ref_stack=_ref_stack) for s in subs)

    # allOf: allow annotation-only subschemas; terminal if:
    # - no subschema is object/array-ish AND
    # - at least one subschema is terminal
    subs = node.get("allOf")
    if isinstance(subs, list) and subs:
        any_terminal = False
        for s in subs:
            if isinstance(s, ABCMapping) and (_is_objectish(s) or _is_arrayish(s)):
                return False
            if _schema_should_be_wrapped(root, s, _ref_stack=_ref_stack):
                any_terminal = True
        return any_terminal

    return False


def _normalize_metadata_schema(metadata_schema: Mapping[str, Any]) -> dict[str, Any]:
    """
    Accept either:
    - a full object schema with "properties"
    - or a mapping of property_name -> subschema (we'll wrap it)
    """

    # full object schema
    if isinstance(metadata_schema, ABCMapping) and isinstance(
        metadata_schema.get("properties"), ABCMapping
    ):
        return dict(metadata_schema)

    # treat as properties dict
    if isinstance(metadata_schema, ABCMapping):
        return {
            "type": "object",
            "properties": dict(metadata_schema),
            "required": list(metadata_schema.keys()),
            "additionalProperties": False,
        }

    raise TypeError(
        "metadata_schema must be a mapping (either a full object schema with 'properties' "
        "or a mapping of metadata_field -> subschema)."
    )


def _is_metadata_wrapper(
    node: Mapping[str, Any],
    *,
    metadata_obj_schema: Mapping[str, Any],
    content_key: str,
) -> bool:
    """
    Structural check: is this node the wrapper we generate?
    If yes, we should NOT recurse into it again (prevents double-wrapping).
    """
    if not isinstance(node, ABCMapping):
        return False

    if node.get("type") != "object":
        return False

    props_any = node.get("properties")
    if not isinstance(props_any, ABCMapping):
        return False
    props = props_any

    if content_key not in props:
        return False

    meta_props_any = metadata_obj_schema.get("properties")
    meta_props = meta_props_any if isinstance(meta_props_any, ABCMapping) else {}
    for k in meta_props.keys():
        if k == content_key:
            continue
        if k not in props:
            return False

    req_any = node.get("required", [])
    if not isinstance(req_any, list):
        return False
    req = {str(x) for x in req_any}
    if content_key not in req:
        return False

    meta_req_any = metadata_obj_schema.get("required", [])
    if isinstance(meta_req_any, list):
        for k in meta_req_any:
            k = str(k)
            if k != content_key and k not in req:
                return False

    return True


def _wrap_value_schema_with_metadata(
    value_schema: Mapping[str, Any],
    *,
    metadata_obj_schema: Mapping[str, Any],
    content_key: str,
    content_description: str | None = None,
) -> dict[str, Any]:
    """
    Construct the wrapper-object schema for a single wrappable value schema.

    This takes the original value constraints (e.g., type/enum/const/$ref + validation
    keywords) and places them under `properties[content_key]`. The remaining properties
    come from `metadata_obj_schema` (e.g., `evidence_anchor`, later `confidence_score`),
    and the wrapper's `required` list is built as:

        ["<content_key>", *metadata_obj_schema["required"]]

    Notes:
    - `title` and `description` from `value_schema` are lifted to the wrapper object so
      that the field-level documentation stays attached to the field, not buried under
      `content`.
    - Optionally, `content_description` can be injected into the inner `content` schema
      to explain the wrapper semantics (e.g., “extracted value; see evidence_anchor”).
    - The wrapper's `additionalProperties` is inherited from `metadata_obj_schema`
      (defaulting to False if absent) to keep the wrapper strict.

    This function assumes `value_schema` is already a "wrappable" schema node (as
    determined by `_schema_should_be_wrapped`); it does not attempt to handle unions,
    nullability, or structural schemas.
    """

    # Copy value schema into content schema, but lift title/description to wrapper
    content_schema = dict(value_schema)
    title = content_schema.pop("title", None)
    description = content_schema.pop("description", None)

    # Optionally attach a description to the inner content field.
    # Note: we popped the original description above (it lives on the wrapper now),
    # so there is no "existing" description on content_schema at this point.
    if content_description is not None:
        content_schema["description"] = content_description

    meta_props_any = metadata_obj_schema.get("properties", {})
    meta_props: dict[str, Any] = (
        dict(meta_props_any) if isinstance(meta_props_any, ABCMapping) else {}
    )

    # If caller included a "content" property in metadata, we override it
    meta_props.pop(content_key, None)

    required_any = metadata_obj_schema.get("required", [])
    meta_required = [str(x) for x in required_any] if isinstance(required_any, list) else []

    additional_props = metadata_obj_schema.get("additionalProperties")
    if additional_props is None:
        additional_props = False

    wrapper: dict[str, Any] = {
        "type": "object",
        "properties": {content_key: content_schema, **meta_props},
        "required": [content_key, *[r for r in meta_required if r != content_key]],
        "additionalProperties": additional_props,
    }

    if title is not None:
        wrapper["title"] = title
    if description is not None:
        wrapper["description"] = description

    return wrapper


WRAPPED_CONTENT_KEY = "content"


def wrap_terminals_with_metadata(
    schema: Mapping[str, Any],
    metadata_schema: Mapping[str, Any],
    *,
    content_key: str = WRAPPED_CONTENT_KEY,
    content_description: str | None = None,
) -> dict[str, Any]:
    """
    Wrap every terminal field schema (scalars/enums/const, including nullable unions and refs)
    into an object containing:
      - <content_key>: the original terminal schema
      - plus metadata fields from `metadata_schema` (default: evidence_anchor: string)

    Notes:
    - Does NOT wrap the root of $defs entries (important for shared enum defs).
    - DOES wrap terminal fields inside object definitions in $defs.
    - Returns a deep-copied dict; input is not mutated.
    """
    from copy import deepcopy

    root: dict[str, Any] = deepcopy(dict(schema))
    metadata_obj_schema = _normalize_metadata_schema(metadata_schema)

    def transform(node: Any, *, allow_wrap_here: bool = True) -> Any:
        if isinstance(node, list):
            return [transform(x, allow_wrap_here=True) for x in node]
        if not isinstance(node, ABCMapping):
            return node

        node_dict: dict[str, Any] = dict(node)

        if _is_metadata_wrapper(
            node_dict, metadata_obj_schema=metadata_obj_schema, content_key=content_key
        ):
            return node_dict

        if isinstance(node_dict.get("type"), list):
            raise ValueError(
                "Encountered JSON Schema 'type' as a list. "
                "This code expects Pydantic-style unions via anyOf/oneOf. "
                "Please normalize type-lists to anyOf/oneOf first or update the wrapper."
            )

        if allow_wrap_here and _schema_should_be_wrapped(root, node_dict):
            return _wrap_value_schema_with_metadata(
                node_dict,
                metadata_obj_schema=metadata_obj_schema,
                content_key=content_key,
                content_description=content_description,
            )

        # combinators
        for k in ("anyOf", "oneOf", "allOf"):
            v = node_dict.get(k)
            if isinstance(v, list):
                node_dict[k] = [transform(s, allow_wrap_here=True) for s in v]

        # object keywords
        props = node_dict.get("properties")
        if isinstance(props, ABCMapping):
            node_dict["properties"] = {
                name: transform(spec, allow_wrap_here=True) for name, spec in props.items()
            }

        pat_props = node_dict.get("patternProperties")
        if isinstance(pat_props, ABCMapping):
            node_dict["patternProperties"] = {
                pat: transform(spec, allow_wrap_here=True) for pat, spec in pat_props.items()
            }

        add_props = node_dict.get("additionalProperties")
        if isinstance(add_props, ABCMapping):
            node_dict["additionalProperties"] = transform(add_props, allow_wrap_here=True)

        uneval_props = node_dict.get("unevaluatedProperties")
        if isinstance(uneval_props, ABCMapping):
            node_dict["unevaluatedProperties"] = transform(uneval_props, allow_wrap_here=True)

        # array keywords
        items = node_dict.get("items")
        if isinstance(items, ABCMapping):
            node_dict["items"] = transform(items, allow_wrap_here=True)

        prefix_items = node_dict.get("prefixItems")
        if isinstance(prefix_items, list):
            node_dict["prefixItems"] = [transform(s, allow_wrap_here=True) for s in prefix_items]

        # other schema-bearing keywords (common)
        for k in ("not", "if", "then", "else", "contains", "propertyNames", "dependentSchemas"):
            v = node_dict.get(k)
            if isinstance(v, ABCMapping):
                node_dict[k] = transform(v, allow_wrap_here=True)
            elif isinstance(v, list):
                node_dict[k] = [transform(x, allow_wrap_here=True) for x in v]

        # defs: don't wrap the *root* of each def, but do transform inside it
        for defs_key in ("$defs", "definitions"):
            defs = node_dict.get(defs_key)
            if isinstance(defs, ABCMapping):
                node_dict[defs_key] = {
                    n: transform(s, allow_wrap_here=False) for n, s in defs.items()
                }

        return node_dict

    return transform(root, allow_wrap_here=True)
