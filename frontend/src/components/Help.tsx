import { Link } from "react-router-dom";
import Icon from "./Icon";

/** Ícone "?" que leva ao termo no glossário (RF10). */
export default function Help({ termo }: { termo: string }) {
  return (
    <Link className="help" to={`/glossario#${encodeURIComponent(termo)}`} title={`O que é ${termo}?`} aria-label={`O que é ${termo}?`}>
      <Icon name="ajuda" size={16} />
    </Link>
  );
}
