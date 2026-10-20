// Eksport terminarza z Łączy Nas Piłka do pliku importu Obsady+.
//
// Uruchamiany jako zakładka (bookmarklet) w przeglądarce użytkownika na stronie
// https://www.laczynaspilka.pl/rozgrywki?... z wybranym sezonem i województwem (ZPN).
// Korzysta z reCAPTCHA i API, które strona i tak wywołuje dla zalogowanego oglądającego,
// pobiera kolejno (z przerwą) rozgrywki ZPN i ich terminarze, a na koniec zapisuje plik
// lnp-terminarz-RRRR-MM-DD.json do wgrania w Obsada+ → Mecze → Importuj.
// Filtrowanie zakresu (IV liga – juniorzy D2) i nadchodzących meczów robi backend.
(async () => {
  const API = "https://competition-api-pro2.laczynaspilka.pl/api/bus/competition/v1/";
  const SITE_KEY = "6Le308YkAAAAAAm1iLONHT8BUz6e9fNgmQ3kxh8f";
  const SKIP = /ekstraklas|\bI{1,3}\s*lig|centraln|\b[EFG]\s*-?\s*[12]\b|orlik|żak|skrzat|futsal|plażow|beach|kobiet|dziewcz|puchar/i;
  const DELAY_MS = 400;

  const params = new URLSearchParams(location.search);
  const season = params.get("season");
  const zpn = params.get("voivodeship");
  const sex = params.get("genderType") || "Male";
  if (!location.hostname.endsWith("laczynaspilka.pl") || !season || !zpn) {
    alert("Otwórz terminarz na laczynaspilka.pl/rozgrywki i wybierz sezon oraz województwo, potem kliknij zakładkę ponownie.");
    return;
  }
  if (!window.grecaptcha?.execute) {
    alert("Strona nie załadowała jeszcze reCAPTCHA. Poczekaj chwilę i spróbuj ponownie.");
    return;
  }

  const banner = document.createElement("div");
  banner.style.cssText = "position:fixed;top:0;left:0;right:0;z-index:99999;padding:10px 16px;background:#312e81;color:#fff;font:14px sans-serif";
  document.body.appendChild(banner);
  const say = (t) => (banner.textContent = "Obsada+: " + t);
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  let token = null;
  let tokenAt = 0;
  const authorize = async () => {
    const key = await new Promise((res) => grecaptcha.ready(() => grecaptcha.execute(SITE_KEY, { action: "token" }).then(res)));
    const r = await fetch(API + "Authorize/recaptcha", { headers: { "x-recaptcha-key": key } });
    if (!r.ok) throw new Error("Autoryzacja reCAPTCHA nie powiodła się (" + r.status + ")");
    const body = await r.text();
    try { token = JSON.parse(body); } catch { token = body; }
    if (typeof token === "object") token = token.token || token.accessToken;
    tokenAt = Date.now();
  };
  const get = async (path, retry = true) => {
    if (!token || Date.now() - tokenAt > 4 * 60 * 1000) await authorize();
    await sleep(DELAY_MS);
    const r = await fetch(API + path, { headers: { Authorization: "Bearer " + token, "Accept-Language": "pl" } });
    if (r.status === 401 && retry) { token = null; return get(path, false); }
    if (!r.ok) throw new Error(path + ": HTTP " + r.status);
    return r.json();
  };
  const list = (x) => (Array.isArray(x) ? x : x?.items || x?.rows || x?.data || x?.results || []);
  const idOf = (o) => o?.id ?? o?.value ?? o?.key;
  const nameOf = (o) => o?.name ?? o?.label ?? o?.text ?? o?.displayName ?? "";
  const brief = (o) => ({ id: idOf(o), name: nameOf(o) });

  try {
    say("pobieram listę rozgrywek…");
    const groups = list(await get(`leagues/seasons/${season}/sexes/${sex}/league-groups`));
    const competitions = [];
    let failed = 0;
    for (const group of groups) {
      if (SKIP.test(nameOf(group))) continue;
      let leagues = [];
      try {
        leagues = list(await get(`seasons/${season}/league-groups/${idOf(group)}/sexes/${sex}/ZPNs/${zpn}/league-dictionaries`));
      } catch { continue; } // grupa bez rozgrywek w tym ZPN
      for (const league of leagues) {
        if (SKIP.test(nameOf(league))) continue;
        let plays = [];
        try {
          plays = list(await get(`leagues/${idOf(league)}/seasons/${season}/ZPNs/${zpn}/play-dictionaries`));
        } catch { /* rozgrywki bez podziału na grupy */ }
        const targets = plays.length ? plays.filter((p) => !SKIP.test(nameOf(p))) : [null];
        for (const play of targets) {
          say(`${nameOf(league)}${play ? " – " + nameOf(play) : ""} (${competitions.length + 1})`);
          try {
            const matches = play
              ? await get(`plays/${idOf(play)}/matches`)
              : await get(`leagues/${idOf(league)}/seasons/${season}/matches`);
            competitions.push({ leagueGroup: brief(group), league: brief(league), play: play && brief(play), matches });
          } catch (e) {
            failed++;
            console.warn("Obsada+", e);
          }
        }
      }
    }
    const today = new Date().toISOString().slice(0, 10);
    const file = { source: "laczynaspilka.pl", exportedAt: new Date().toISOString(), season: { id: season }, zpn: { id: zpn }, sex, competitions };
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(file)], { type: "application/json" }));
    a.download = `lnp-terminarz-${today}.json`;
    a.click();
    say(`gotowe: ${competitions.length} rozgrywek${failed ? `, ${failed} nie udało się pobrać (szczegóły w konsoli)` : ""}. Plik wgraj w Obsada+ → Mecze → Importuj.`);
  } catch (e) {
    say("błąd: " + e.message);
    console.error(e);
  }
  setTimeout(() => banner.remove(), 15000);
})();
