import { FileText, Receipt } from 'lucide-react';
import './ui.css';

function DocTypeBadge({ type = 'dum', label }) {
	const isInvoice = type === 'invoice';
	const text = label || (isInvoice ? 'Facture' : 'DUM');
	return (
		<span className={`emp-badge emp-badge--${isInvoice ? 'invoice' : 'dum'}`}>
			{isInvoice ? <Receipt size={12} /> : <FileText size={12} />}
			{text}
		</span>
	);
}

export default DocTypeBadge;
