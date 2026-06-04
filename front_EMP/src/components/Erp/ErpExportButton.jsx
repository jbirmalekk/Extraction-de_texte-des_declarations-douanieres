import { Database } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
	ERP_EXPORT,
	getErpExportLabel,
	navigateToErpSuccess,
	requestDossierErpExport,
} from '../../utils/erpExport';
import './ErpExportButton.css';

function ErpExportButton({
	kind = ERP_EXPORT.DOSSIER,
	invoiceId = null,
	dumId = null,
	documentId = null,
	reference = null,
	statutControle = null,
	isAmountAligned = true,
	isAdmin = false,
	disabled = false,
	className = '',
	block = false,
	onError,
	onClick,
	children,
}) {
	const navigate = useNavigate();
	const label = children || getErpExportLabel(kind);

	const handleClick = () => {
		if (onClick) {
			onClick();
			return;
		}

		if (kind === ERP_EXPORT.DOSSIER) {
			requestDossierErpExport({
				navigate,
				statutControle,
				isAmountAligned,
				isAdmin,
				invoiceId,
				dumId,
				reference,
				onError,
			});
			return;
		}

		navigateToErpSuccess(navigate, {
			kind,
			invoiceId: kind === ERP_EXPORT.INVOICE ? invoiceId ?? documentId : null,
			dumId: kind === ERP_EXPORT.DUM ? dumId ?? documentId : null,
			documentId: documentId ?? dumId ?? invoiceId,
			reference,
		});
	};

	const classes = [
		'erp-export-btn',
		`erp-export-btn--${kind}`,
		block ? 'erp-export-btn--block' : '',
		className,
	]
		.filter(Boolean)
		.join(' ');

	return (
		<button
			type="button"
			className={classes}
			onClick={handleClick}
			disabled={disabled}
			title={disabled ? 'Validez le document avant l’export ERP' : undefined}
		>
			<Database size={16} />
			{label}
		</button>
	);
}

export default ErpExportButton;
