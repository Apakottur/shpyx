module.exports = {
  plugins: [],
  extends: ["plugin:toml/standard"],
  overrides: [
    {
      files: ["*.toml"],
      parser: "toml-eslint-parser"
    }
  ],
  rules: {}
};
