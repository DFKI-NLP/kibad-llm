import logging
from pathlib import Path

logging.getLogger().setLevel(logging.INFO)

for src_path in Path("./src").rglob("*"):
    if src_path.stem.startswith("__") and src_path.stem.endswith("__"):
        # skip dunder files
        continue
    if src_path.parent == Path("./src/kibad_llm/utils"):
        # skip specific files
        continue
    if src_path.is_file() and src_path.suffix == ".py":
        dest_path = Path("./docs") / src_path.relative_to(
            "./src"
        ).with_suffix(".md")
        if not dest_path.is_file():
            logging.info(
                f"Creating basic doc file for {src_path} at {dest_path}"
            )
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_text(
                f":::{src_path.relative_to('./src').with_suffix('').__str__().replace('/','.')}"
            )
