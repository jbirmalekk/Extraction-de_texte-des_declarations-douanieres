import { useRef, useState } from 'react';

function DropZone({ onFileDrop, accept = '.pdf,image/*', disabled = false }) {
	const inputRef = useRef(null);
	const [isDragging, setIsDragging] = useState(false);

	const handleDragOver = (event) => {
		event.preventDefault();
		if (disabled) {
			return;
		}
		setIsDragging(true);
	};

	const handleDragLeave = (event) => {
		event.preventDefault();
		setIsDragging(false);
	};

	const handleDrop = (event) => {
		event.preventDefault();
		if (disabled) {
			return;
		}
		setIsDragging(false);
		const file = event.dataTransfer?.files?.[0];
		if (file) {
			onFileDrop?.(file);
		}
	};

	const handleFileSelect = (event) => {
		const file = event.target.files?.[0];
		if (file) {
			onFileDrop?.(file);
			// Reset the input so the same file can be re-selected if needed
			event.target.value = '';
		}
	};

	return (
		<div
			className={`dropzone ${isDragging ? 'dragging' : ''} ${disabled ? 'disabled' : ''}`}
			onDragOver={handleDragOver}
			onDragLeave={handleDragLeave}
			onDrop={handleDrop}
		>
			<div className="dropzone-content">
				<p className="dropzone-title">Glissez-deposez votre fichier</p>
				<p className="dropzone-subtitle">ou cliquez pour parcourir votre ordinateur</p>
				<button
					type="button"
					className="dropzone-button"
					onClick={() => inputRef.current?.click()}
					disabled={disabled}
				>
					Choisir un fichier
				</button>
				<p className="dropzone-hint">Formats supportes : PDF, JPG, PNG (max 25 MB)</p>
			</div>
			<input
				type="file"
				ref={inputRef}
				className="dropzone-input"
				accept={accept}
				onChange={handleFileSelect}
				disabled={disabled}
			/>
		</div>
	);
}

export default DropZone;
