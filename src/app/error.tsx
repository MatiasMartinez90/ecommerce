"use client";

export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <main className="page">
      <div className="empty">
        <p className="eyebrow">Error temporal</p>
        <h1>No pudimos cargar la tienda.</h1>
        <p>Reintentá en unos segundos. Tu carrito sigue guardado.</p>
        <button className="button" type="button" onClick={reset}>Reintentar</button>
      </div>
    </main>
  );
}
