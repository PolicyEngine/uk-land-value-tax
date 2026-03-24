export default function SectionHeading({ title, description }) {
  return (
    <div className="mb-5">
      <h2 className="text-xl font-semibold tracking-tight text-slate-900">{title}</h2>
      {description ? (
        <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
      ) : null}
    </div>
  );
}
