import { useCallback, useState } from 'react';
import Cropper from 'react-easy-crop';

const createImage = (url) =>
	new Promise((resolve, reject) => {
		const image = new Image();
		image.onload = () => resolve(image);
		image.onerror = () => reject(new Error("Impossible de charger l'image."));
		image.src = url;
	});

const getRadianAngle = (degreeValue) => (degreeValue * Math.PI) / 180;

const rotateSize = (width, height, rotation) => ({
	width: Math.abs(Math.cos(rotation) * width) + Math.abs(Math.sin(rotation) * height),
	height: Math.abs(Math.sin(rotation) * width) + Math.abs(Math.cos(rotation) * height),
});

const transformWholeImageToBlob = async (imageUrl, rotation = 0, zoom = 1, cropAreaPixels) => {
	const image = await createImage(imageUrl);
	const rotationRadian = getRadianAngle(rotation);
	const scaledWidth = image.width * zoom;
	const scaledHeight = image.height * zoom;
	const rotatedImageSize = rotateSize(scaledWidth, scaledHeight, rotationRadian);

	const canvas = document.createElement('canvas');
	const context = canvas.getContext('2d');
	if (!context) {
		throw new Error("Le navigateur ne supporte pas l'edition d'image.");
	}

	canvas.width = rotatedImageSize.width;
	canvas.height = rotatedImageSize.height;
	context.translate(rotatedImageSize.width / 2, rotatedImageSize.height / 2);
	context.rotate(rotationRadian);
	context.fillStyle = '#ffffff';
	context.fillRect(
		-rotatedImageSize.width / 2,
		-rotatedImageSize.height / 2,
		rotatedImageSize.width,
		rotatedImageSize.height
	);
	context.drawImage(
		image,
		-scaledWidth / 2,
		-scaledHeight / 2,
		scaledWidth,
		scaledHeight
	);

	const outputCanvas = document.createElement('canvas');
	const outputCtx = outputCanvas.getContext('2d');
	if (!outputCtx) {
		throw new Error("Le navigateur ne supporte pas l'edition d'image.");
	}

	if (cropAreaPixels) {
		const cropW = Math.max(1, Math.round(cropAreaPixels.width));
		const cropH = Math.max(1, Math.round(cropAreaPixels.height));
		outputCanvas.width = cropW;
		outputCanvas.height = cropH;
		outputCtx.fillStyle = '#ffffff';
		outputCtx.fillRect(0, 0, cropW, cropH);
		outputCtx.drawImage(
			canvas,
			Math.round(cropAreaPixels.x),
			Math.round(cropAreaPixels.y),
			cropW,
			cropH,
			0,
			0,
			cropW,
			cropH
		);
	} else {
		outputCanvas.width = canvas.width;
		outputCanvas.height = canvas.height;
		outputCtx.drawImage(canvas, 0, 0);
	}

	return new Promise((resolve, reject) => {
		outputCanvas.toBlob(
			(blob) => {
				if (!blob) {
					reject(new Error("Impossible de generer l'image ajustee."));
					return;
				}
				resolve(blob);
			},
			'image/jpeg',
			0.95
		);
	});
};

function ImageCropper({ imageUrl, sourceFile, fileLabel, disabled = false, onCropApplied }) {
	const [crop, setCrop] = useState({ x: 0, y: 0 });
	const [zoom, setZoom] = useState(1);
	const [rotation, setRotation] = useState(0);
	const [aspect, setAspect] = useState(0.75);
	const [croppedAreaPixels, setCroppedAreaPixels] = useState(null);
	const [isCropping, setIsCropping] = useState(false);

	const handleCropComplete = useCallback((_area, areaPixels) => {
		setCroppedAreaPixels(areaPixels);
	}, []);

	const applyCrop = async () => {
		if (disabled || !sourceFile || !croppedAreaPixels) {
			return;
		}
		setIsCropping(true);
		try {
			const blob = await transformWholeImageToBlob(imageUrl, rotation, zoom, croppedAreaPixels);
			const extension = sourceFile.name.split('.').pop() || 'jpg';
			const fileName = `${sourceFile.name.replace(/\.[^/.]+$/, '')}_cropped.${extension}`;
			const croppedFile = new File([blob], fileName, {
				type: blob.type || sourceFile.type || 'image/jpeg',
				lastModified: Date.now(),
			});
			onCropApplied?.({ croppedFile, rotation, zoom, crop: croppedAreaPixels });
		} catch (error) {
			onCropApplied?.({ error });
		} finally {
			setIsCropping(false);
		}
	};

	return (
		<section className="image-cropper-panel">
			<div className="image-cropper-head">
				<p className="import-panel-kicker">Etape 2</p>
				<h3>Cadrage personnalise du document</h3>
				{fileLabel ? <p className="image-cropper-file-label">{fileLabel}</p> : null}
			</div>
			<div className="image-cropper-stage">
				<Cropper
					image={imageUrl}
					crop={crop}
					zoom={zoom}
					rotation={rotation}
					aspect={aspect}
					onCropChange={setCrop}
					onCropComplete={handleCropComplete}
					onZoomChange={setZoom}
					onRotationChange={setRotation}
					cropShape="rect"
					showGrid
					objectFit="contain"
				/>
			</div>
			<div className="image-cropper-controls">
				<label htmlFor="crop-aspect-range">Ratio du cadre ({aspect.toFixed(2)})</label>
				<input
					id="crop-aspect-range"
					type="range"
					min={0.4}
					max={2}
					step={0.01}
					value={aspect}
					onChange={(event) => setAspect(Number(event.target.value))}
					disabled={disabled || isCropping}
				/>
				<label htmlFor="crop-zoom-range">Zoom</label>
				<input
					id="crop-zoom-range"
					type="range"
					min={0.5}
					max={2}
					step={0.01}
					value={zoom}
					onChange={(event) => setZoom(Number(event.target.value))}
					disabled={disabled || isCropping}
				/>
				<label htmlFor="crop-rotation-range">Rotation</label>
				<input
					id="crop-rotation-range"
					type="range"
					min={-180}
					max={180}
					step={1}
					value={rotation}
					onChange={(event) => setRotation(Number(event.target.value))}
					disabled={disabled || isCropping}
				/>
				<div className="image-cropper-actions">
					<button
						type="button"
						className="crop-reset-button"
						onClick={() => {
							setCrop({ x: 0, y: 0 });
							setZoom(1);
							setRotation(0);
							setAspect(0.75);
						}}
						disabled={disabled || isCropping}
					>
						Reinitialiser
					</button>
					<button
						type="button"
						className="auth-button crop-apply-button"
						onClick={applyCrop}
						disabled={disabled || isCropping || !croppedAreaPixels}
					>
						{isCropping ? 'Application...' : 'Appliquer le rognage'}
					</button>
				</div>
			</div>
		</section>
	);
}

export default ImageCropper;
