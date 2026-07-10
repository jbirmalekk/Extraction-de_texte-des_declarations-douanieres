import { useEffect, useRef, useState } from 'react';
import { Database } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
	ERP_EXPORT,
	getErpExportGate,
	getErpExportLabel,
	requestErpExport,
} from '@/shared/utils/erpExport';
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
	const wrapRef = useRef(null);
	const [isExporting, setIsExporting] = useState(false);
	const [showConfirm, setShowConfirm] = useState(false);
	const [confirmMessage, setConfirmMessage] = useState('');
	const label = children || getErpExportLabel(kind);

	useEffect(() => {
		if (!showConfirm) {
			return undefined;
		}
		const onKeyDown = (event) => {
			if (event.key === 'Escape') {
				setShowConfirm(false);
			}
		};
		const onPointerDown = (event) => {
			if (wrapRef.current && !wrapRef.current.contains(event.target)) {
				setShowConfirm(false);
			}
		};
		document.addEventListener('keydown', onKeyDown);
		document.addEventListener('mousedown', onPointerDown);
		return () => {
			document.removeEventListener('keydown', onKeyDown);
			document.removeEventListener('mousedown', onPointerDown);
		};
	}, [showConfirm]);

	const runExport = async () => {
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

	const handleOpenConfirm = () => {
		if (onClick) {
			onClick();
			return;
		}
		if (isExporting || disabled) {
			return;
		}

		const gate = getErpExportGate({ kind, statutControle, isAmountAligned, isAdmin });
		if (!gate.allowed) {
			onError?.(gate.reason);
			return;
		}

		setConfirmMessage(gate.confirmMessage);
		setShowConfirm(true);
	};

	const handleConfirm = async () => {
		setShowConfirm(false);
		await runExport();
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
		<div className="erp-export-wrap" ref={wrapRef}>
			<button
				type="button"
				className={classes}
				onClick={handleOpenConfirm}
				disabled={disabled || isExporting}
				title={disabled ? 'Validez le document avant l’export ERP' : undefined}
				aria-expanded={showConfirm}
			>
				<Database size={16} />
				{isExporting ? 'Intégration ERP…' : label}
			</button>

			{showConfirm ? (
				<div
					className="erp-export-confirm"
					role="dialog"
					aria-modal="true"
					aria-labelledby="erp-export-confirm-title"
				>
					<p id="erp-export-confirm-title" className="erp-export-confirm__text">
						{confirmMessage}
					</p>
					<div className="erp-export-confirm__actions">
						<button
							type="button"
							className="erp-export-confirm__btn erp-export-confirm__btn--ghost"
							onClick={() => setShowConfirm(false)}
							disabled={isExporting}
						>
							Annuler
						</button>
						<button
							type="button"
							className="erp-export-confirm__btn erp-export-confirm__btn--primary"
							onClick={handleConfirm}
							disabled={isExporting}
						>
							Confirmer l’intégration
						</button>
					</div>
				</div>
			) : null}
		</div>
	);
}

export default ErpExportButton;
