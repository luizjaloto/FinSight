import { Link } from "react-router-dom";

/** Ícone "?" que leva ao termo no glossário (RF10). */
export default function Help({ termo }: { termo: string }) {
  return (
    <Link className="help" to={`/glossario#${encodeURIComponent(termo)}`} title={`O que é ${termo}?`} aria-label={`O que é ${termo}?`}>
      ?
    </Link>
  );
}
