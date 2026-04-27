async function getData() {
  const base = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const res = await fetch(`${base}/propicks/edges/today`, { cache: 'no-store' });
  if (!res.ok) return { rows: [] };
  return res.json();
}
export default async function Page() {
  const data = await getData();
  const rows = data.rows || [];
  return <main style={{padding:24}}>
    <h1>Dashboard ProPicksMLB</h1>
    <p>Moneyline / Run Line / Totals / F5 / Team Runs</p>
    <pre style={{background:'#111827', border:'1px solid #334155', borderRadius:16, padding:16, whiteSpace:'pre-wrap'}}>{JSON.stringify(rows.slice(0,25), null, 2)}</pre>
  </main>;
}
