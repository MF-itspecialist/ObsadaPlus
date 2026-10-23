import { AccountBox } from "../components/Layout";
import { useAuth } from "../context/AuthContext";

/** Strona startowa konta sędziego. Panel z obsadą i dyspozycyjnością — kolejny etap. */
export default function RefereeHomePage() {
  const { user } = useAuth();
  return (
    <div className="mx-auto max-w-xl px-4 py-12">
      <div className="card overflow-hidden">
        <div className="p-7">
          <h1 className="text-xl font-semibold tracking-tight">Witaj, {user?.referee_name ?? user?.display_name}</h1>
          <p className="mt-2 text-sm text-zinc-600">
            Twoje konto sędziego jest aktywne. Wkrótce zobaczysz tu swoje mecze i zgłosisz dyspozycyjność na kolejne weekendy.
          </p>
        </div>
        <AccountBox />
      </div>
    </div>
  );
}
