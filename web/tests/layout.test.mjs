import fs from "fs";
import path from "path";
import assert from "assert";

const requiredComponents = [
  "src/layouts/BaseLayout.astro",
  "src/components/Header.astro",
  "src/components/Footer.astro",
  "src/components/Hero.astro"
];

requiredComponents.forEach(file => {
  const p = path.resolve(file);
  assert.ok(fs.existsSync(p), `Componente ${file} deve existir`);
  const content = fs.readFileSync(p, "utf-8");
  assert.ok(content.length > 50, `Componente ${file} deve ter conteúdo substancial`);
});

console.log("✅ Teste de componentes estruturais aprovado!");
