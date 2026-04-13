import apiClient from './api';

export const extractOcrDocument = async (
	file,
	{ fastMode = false, useDeskew = true, onUploadProgress } = {}
) => {
	const formData = new FormData();
	formData.append('file', file);

	const { data } = await apiClient.post('/api/ocr', formData, {
		params: {
			fast_mode: fastMode,
			use_deskew: useDeskew,
		},
		headers: {
			'Content-Type': 'multipart/form-data',
		},
		onUploadProgress,
	});

	return data;
};

export const validateOcrDocument = async (documentId, payload) => {
	const { data } = await apiClient.put(`/api/ocr/${documentId}/valider`, payload);
	return data;
};
