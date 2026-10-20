import { Pencil, Trash2 } from "lucide-react";

/** Przyciski „Edytuj” i „Usuń” w wierszu tabeli — jednakowe we wszystkich widokach. */
export default function RowActions({ onEdit, onDelete }: { onEdit: () => void; onDelete: () => void }) {
  return (
    <div className="flex justify-end gap-1">
      <button type="button" className="icon-btn" onClick={onEdit} aria-label="Edytuj" title="Edytuj">
        <Pencil className="size-4" />
      </button>
      <button type="button" className="icon-btn hover:bg-red-50 hover:text-red-600" onClick={onDelete} aria-label="Usuń" title="Usuń">
        <Trash2 className="size-4" />
      </button>
    </div>
  );
}
