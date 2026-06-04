import { useState } from 'react';
import { Database } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
	ERP_EXPORT,
	getErpExportLabel,
	requestErpExport,
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
	const [isExporting, setIsExporting] = useState(false);
	const label = children || getErpExportLabel(kind);

	const handleClick = async () => {
		if (onClick) {
			onClick();
			return;
		}
		if (isExporting || disabled) {
			return;
		}

		setIsExporting(true);
		try {
			await requestErpExport({
				navigate,
				kind,
				statutControle,
				isAmountAligned,
				isAdmin,
				invoiceId,
				dumId,
				documentId,
				reference,
				onError,
			});
		} finally {
			setIsExporting(false);
		}
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
			disabled={disabled || isExporting}
			title={disabled ? 'Validez le document avant l’export ERP' : undefined}
		>
			<Database size={16} />
			{isExporting ? 'Intégration ERP…' : label}
		</button>
	);
}

export default ErpExportButton;
