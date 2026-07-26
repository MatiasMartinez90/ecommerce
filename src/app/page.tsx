import { getStoreConfig } from "@/config/store";

export default function Home() {
  const config = getStoreConfig();
  return (
    <main className="shell">
      <section className="card" aria-labelledby="store-title">
        <span className="eyebrow">{config.brand.shortName}</span>
        <h1 id="store-title">{config.brand.name}</h1>
        <p>{config.brand.description}</p>
        <p>{config.pickup.label}: {config.pickup.address}</p>
        <a href={config.links.mainSite}>Volver al sitio principal</a>
      </section>
    </main>
  );
}
