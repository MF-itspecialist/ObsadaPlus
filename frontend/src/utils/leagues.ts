// Poziom rozgrywek z nazwy ligi (jak w backendzie: optimization/licenses.py), do grupowania obsady.

export interface LeagueLevel {
  rank: number; // niżej = wyższa liga
  label: string;
}

const ROMAN: Record<string, [number, string]> = {
  i: [2, "I liga"],
  ii: [3, "II liga"],
  iii: [4, "III liga"],
  iv: [5, "IV liga"],
  v: [6, "V liga"],
};
const YOUTH = /junior|trampkarz|młodzik|mlodzik|orlik|żak|skrzat|\bu-?\d{1,2}\b|młodzież/;

export function leagueLevel(league: string): LeagueLevel {
  const text = league.toLowerCase().trim();
  if (!text) return { rank: 99, label: "Bez ligi" };
  if (text.includes("futsal") || text.includes("plażow")) return { rank: 21, label: "Futsal i piłka plażowa" };
  if (text.includes("kobiet")) return { rank: 20, label: "Piłka kobiet" };
  if (YOUTH.test(text)) return { rank: 30, label: "Rozgrywki młodzieżowe" };
  if (text.includes("ekstraklasa")) return { rank: 1, label: "Ekstraklasa" };
  if (text.includes("okręgow") || text.includes("okregow")) return { rank: 7, label: "Klasa okręgowa" };
  const roman = text.match(/\b(i{1,3}|iv|v)\s+liga\b/);
  if (roman) {
    const [rank, label] = ROMAN[roman[1]];
    return { rank, label };
  }
  if (/klas[ay]\s*a\b/.test(text)) return { rank: 8, label: "Klasa A" };
  if (/klas[ay]\s*b\b/.test(text)) return { rank: 9, label: "Klasa B" };
  if (/klas[ay]\s*c\b/.test(text)) return { rank: 10, label: "Klasa C" };
  return { rank: 50, label: "Inne rozgrywki" };
}

/** Tekst do wyszukiwania: małe litery, bez polskich znaków. */
export function normalize(text: string): string {
  return text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/ł/g, "l");
}
