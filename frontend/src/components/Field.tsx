interface FieldProps {
  id: string;
  label: string;
  placeholder: string;
  maxLength: number;
  rows: number;
  value: string;
  onChange: (value: string) => void;
  fill?: "base" | "large";
  short?: boolean;
}

export function Field({
  id,
  label,
  placeholder,
  maxLength,
  rows,
  value,
  onChange,
  fill,
  short,
}: FieldProps) {
  const fieldClass = [
    "gl-field",
    fill && "gl-field--fill",
    fill === "large" && "gl-field--fill-lg",
  ]
    .filter(Boolean)
    .join(" ");

  const textareaClass = ["gl-textarea", short && "gl-textarea--short"]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={fieldClass}>
      <div className="gl-field-head">
        <label className="gl-label" htmlFor={id}>
          {label}
        </label>
        <span className="gl-counter" aria-hidden="true">
          {value.length} / {maxLength}
        </span>
      </div>
      <textarea
        className={textareaClass}
        id={id}
        rows={rows}
        placeholder={placeholder}
        required
        maxLength={maxLength}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
