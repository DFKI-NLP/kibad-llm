export class FakeElement {
  constructor(tagName) {
    this.tagName = tagName.toLowerCase();
    this.children = [];
    this.parentElement = null;
    this.attributes = new Map();
    this.listeners = new Map();
    this.style = {};
    this.textContent = "";
    this.className = "";
    this.title = "";
    this.type = "";
    this.value = "";
    this.hidden = false;
    this.offsetWidth = 80;
    this.offsetHeight = 20;
    this.isConnected = true;
    this.clicked = false;
    this.selected = false;
    this.focused = false;
    this._bbox = { x: 0, y: 0, width: 100, height: 50 };
  }

  get firstChild() {
    return this.children[0] || null;
  }

  get childElementCount() {
    return this.children.length;
  }

  set innerHTML(value) {
    this.children = [];
    this.textContent = value;
  }

  appendChild(child) {
    child.parentElement = this;
    this.children.push(child);
    return child;
  }

  insertBefore(child, beforeChild) {
    child.parentElement = this;
    const index = this.children.indexOf(beforeChild);
    if (index === -1) {
      this.children.push(child);
    } else {
      this.children.splice(index, 0, child);
    }
    return child;
  }

  removeChild(child) {
    this.children = this.children.filter((candidate) => candidate !== child);
    child.parentElement = null;
    return child;
  }

  remove() {
    this.parentElement?.removeChild(this);
  }

  setAttribute(name, value) {
    this.attributes.set(name, String(value));
    if (name === "class") {
      this.className = String(value);
    }
  }

  getAttribute(name) {
    if (name === "class") {
      return this.className;
    }
    return this.attributes.get(name) || null;
  }

  hasAttribute(name) {
    return this.attributes.has(name) || (name === "class" && Boolean(this.className));
  }

  addEventListener(type, listener) {
    this.listeners.set(type, listener);
  }

  dispatch(type, event = {}) {
    return this.listeners.get(type)?.(event);
  }

  click() {
    this.clicked = true;
    return this.dispatch("click", { clientX: 1, clientY: 1 });
  }

  focus() {
    this.focused = true;
  }

  select() {
    this.selected = true;
  }

  getBoundingClientRect() {
    return {
      width: Number(this.getAttribute("width") || 0),
      height: Number(this.getAttribute("height") || 0),
    };
  }

  getBBox() {
    return this._bbox;
  }

  cloneNode(deep = false) {
    const clone = new FakeElement(this.tagName);
    clone.className = this.className;
    clone.textContent = this.textContent;
    clone.title = this.title;
    clone.type = this.type;
    clone.value = this.value;
    clone.style = { ...this.style };
    clone._bbox = { ...this._bbox };
    for (const [name, value] of this.attributes.entries()) {
      clone.attributes.set(name, value);
    }
    if (deep) {
      for (const child of this.children) {
        clone.appendChild(child.cloneNode(true));
      }
    }
    return clone;
  }

  querySelector(selector) {
    return this.querySelectorAll(selector)[0] || null;
  }

  querySelectorAll(selector) {
    const matches = [];
    const visit = (element) => {
      if (matchesSelector(element, selector)) {
        matches.push(element);
      }
      for (const child of element.children) {
        visit(child);
      }
    };
    visit(this);
    return matches;
  }
}

export function createDocumentStub() {
  const body = new FakeElement("body");
  const documentElement = new FakeElement("html");
  return {
    body,
    documentElement,
    fonts: { ready: Promise.resolve() },
    createElement: (tagName) => {
      if (tagName === "canvas") {
        const canvas = new FakeElement("canvas");
        canvas.getContext = () => ({
          font: "",
          measureText: (text) => ({ width: text.length * 8 }),
        });
        return canvas;
      }
      return new FakeElement(tagName);
    },
    createElementNS: (_namespace, tagName) => new FakeElement(tagName),
    execCommand: () => true,
  };
}

export function serializeFakeSvg(svg) {
  const attributes = Array.from(svg.attributes.entries())
    .map(([name, value]) => `${name}="${value}"`)
    .join(" ");
  const children = svg.children.map((child) => serializeFakeSvg(child)).join("");
  const content = `${svg.textContent || ""}${children}`;
  return attributes.length
    ? `<${svg.tagName} ${attributes}>${content}</${svg.tagName}>`
    : `<${svg.tagName}>${content}</${svg.tagName}>`;
}

function matchesSelector(element, selector) {
  if (selector.startsWith(".")) {
    const classNames = selector.slice(1).split(".");
    const elementClasses = String(element.className || "").split(/\s+/);
    return classNames.every((className) => elementClasses.includes(className));
  }
  return element.tagName === selector.toLowerCase();
}
