"use strict";

const fs = require("fs");
const path = require("path");
const Handlebars = require("handlebars");

const MAX_INPUT = 48 * 1024;
const POSTCARD_LAYOUT = fs.readFileSync(
  path.join(__dirname, "templates", "postcard-layout.hbs"),
  "utf8"
);

function mergeTheme(target, source) {
  for (const [key, value] of Object.entries(source)) {
    if (value !== null && typeof value === "object") {
      target[key] ??= Array.isArray(value) ? [] : {};
      mergeTheme(target[key], value);
    } else {
      target[key] = value;
    }
  }
  return target;
}

function render(job) {
  const theme = mergeTheme({}, job.theme);
  const writableProperties = {
    title: true,
    accent: true,
    caption: true,
  };

  Handlebars.registerHelper("setLayoutOption", function (target, options) {
    const key = options.hash.key;
    const value = options.hash.value;

    if (typeof key !== "string" || !writableProperties[key]) {
      throw new Error("Theme property is not writable");
    }
    if (target === null || (typeof target !== "object" && typeof target !== "function")) {
      throw new Error("Theme target is invalid");
    }

    target[key] = value;
    return "";
  });

  if (typeof job.template !== "string") {
    throw new Error("Template source must be text");
  }

  const template = Handlebars.compile(job.template, {
    preventIndent: true,
  });

  const rootData = Object.create(null);
  Object.defineProperty(rootData, "partial-block", {
    value: undefined,
    enumerable: true,
    writable: true,
    configurable: true,
  });

  const safePartials = Object.create(null);
  Object.defineProperty(safePartials, "myPartial", {
    value: POSTCARD_LAYOUT,
    enumerable: true,
    writable: false,
    configurable: false,
  });

  return template({ ...job.model, theme }, {
    data: rootData,
    partials: safePartials,
    allowProtoMethodsByDefault: false,
    allowProtoPropertiesByDefault: false,
  });
}

if (require.main === module) {
  let input = "";
  process.stdin.setEncoding("utf8");
  process.stdin.on("data", (chunk) => {
    input += chunk;
    if (Buffer.byteLength(input) > MAX_INPUT) {
      process.stderr.write("Input limit exceeded\n");
      process.exit(1);
    }
  });
  process.stdin.on("end", () => {
    try {
      const output = render(JSON.parse(input));
      process.stdout.write(JSON.stringify({ ok: true, output }));
    } catch (error) {
      process.stdout.write(JSON.stringify({ ok: false, error: error.message }));
      process.exitCode = 1;
    }
  });
}

module.exports = { mergeTheme, render };
