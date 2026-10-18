import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useListReflow } from "./use-list-reflow";
import "./shopping-list.css";

// Temporary sample content for the add-items test action.
const SAMPLE_ITEMS = [
  "Milk", "Eggs", "Bread", "Butter", "Cheddar cheese",
  "Yoghurt", "Bananas", "Apples", "Oranges", "Potatoes",
  "Onions", "Carrots", "Tomatoes", "Spinach", "Chicken breast",
  "Rice", "Pasta", "Olive oil", "Coffee", "Toilet roll",
];

type Item = { id: number; text: string; removing?: boolean };

export function ShoppingList({ sampleRequest }: { sampleRequest: number }) {
  const [items, setItems] = useState<Item[]>([{ id: 0, text: "" }]);
  const reflow = useListReflow(items);
  const latestItems = useRef(items);
  useLayoutEffect(() => { latestItems.current = items; }, [items]);
  const collapseTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const nextId = useRef(1);

  function waitForBackspacePause() {
    if (collapseTimer.current !== null) clearTimeout(collapseTimer.current);
    collapseTimer.current = setTimeout(() => {
      collapseTimer.current = null;
      if (!latestItems.current.some((row) => row.removing)) return;
      reflow.capture();
      setItems((current) => current.filter((row) => !row.removing));
    }, 300);
  }

  useEffect(() => () => {
    if (collapseTimer.current !== null) clearTimeout(collapseTimer.current);
  }, []);
  const inputs = useRef(new Map<number, HTMLInputElement>());
  const pendingFocus = useRef<{ id: number; caret: number } | null>(null);

  useLayoutEffect(() => {
    const pending = pendingFocus.current;
    if (!pending) return;
    const input = inputs.current.get(pending.id);
    if (!input) throw new Error("Shopping item input was not mounted");
    input.focus();
    input.setSelectionRange(pending.caret, pending.caret);
    pendingFocus.current = null;
  }, [items]);

  useEffect(() => {
    if (sampleRequest === 0) return;
    pendingFocus.current = null;
    if (collapseTimer.current !== null) clearTimeout(collapseTimer.current);
    collapseTimer.current = null;
    setItems(SAMPLE_ITEMS.map((text) => ({ id: nextId.current++, text })));
  }, [sampleRequest]);

  return (
    <>
    <ul className="shopping-list" aria-label="Shopping list">
      {items.map((item, index) => (
        <li
          key={item.id}
          ref={(element) => {
            if (element) reflow.rows.current.set(item.id, element);
            else reflow.rows.current.delete(item.id);
          }}
          className={item.removing ? "is-removing" : undefined}
          aria-hidden={item.removing || undefined}

        >
          {item.removing && <BulletPop />}
          <input
            disabled={item.removing}
            ref={(element) => {
              if (element) inputs.current.set(item.id, element);
              else inputs.current.delete(item.id);
            }}
            type="text"
            aria-label={`Shopping item ${index + 1}`}
            value={item.text}
            enterKeyHint="next"
            autoComplete="off"
            onChange={(event) => {
              const text = event.target.value;
              setItems((current) => current.map((row) => row.id === item.id ? { ...row, text } : row));
            }}
            onBeforeInput={(event) => {
              if ((event.nativeEvent as InputEvent).inputType === "deleteContentBackward") waitForBackspacePause();
            }}
            onKeyUp={(event) => {
              if (event.key === "Backspace") waitForBackspacePause();
            }}
            onKeyDown={(event) => {
              if (event.nativeEvent.isComposing) return;
              if (event.key === "Backspace") waitForBackspacePause();
              if (event.key === "Enter") {
                event.preventDefault();
                const start = event.currentTarget.selectionStart ?? item.text.length;
                const end = event.currentTarget.selectionEnd ?? start;
                const next = { id: nextId.current++, text: item.text.slice(end) };
                pendingFocus.current = { id: next.id, caret: 0 };
                setItems((current) => [
                  ...current.slice(0, index),
                  { ...item, text: item.text.slice(0, start) },
                  next,
                  ...current.slice(index + 1),
                ]);
              } else if (event.key === "Backspace" && item.text === "" && index > 0) {
                event.preventDefault();
                const previous = items.slice(0, index).findLast((row) => !row.removing);
                if (!previous) return;
                pendingFocus.current = { id: previous.id, caret: previous.text.length };
                // Pop now; keep the gap until backspacing has paused.
                setItems((current) => current.map((row) => row.id === item.id ? { ...row, removing: true } : row));
              }
            }}
          />
        </li>
      ))}

    </ul>
    </>
  );
}

function BulletPop() {
  return (
    <span className="bullet-pop" aria-hidden="true">
      <span className="bullet-pop-dot" />
      <svg className="bullet-pop-rays" width="29" height="29" viewBox="0 0 24 24" aria-hidden="true">
        {Array.from({ length: 6 }, (_, index) => (
          <g key={index} transform={`rotate(${index * 60} 12 12)`}>
            <line x1="15" y1="12" x2="18" y2="12" />
          </g>
        ))}
      </svg>
    </span>
  );
}
