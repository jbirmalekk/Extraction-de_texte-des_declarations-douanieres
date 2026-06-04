/** Champ à corriger : vide, confiance faible, erreur ou modifié par rapport à l'OCR. */
export const fieldNeedsCorrection = (field) => {
	const empty = !String(field?.value ?? '').trim();
	const lowConf = typeof field.confidence === 'number' && field.confidence < 80;
	const hasError = Boolean(field?.hasError);
	const diverged =
		String(field?.value ?? '').trim() !== String(field?.ocrOriginal ?? '').trim();
	return empty || lowConf || hasError || diverged;
};

export const sortValidationFields = (fields, sortBy = 'section') => {
	const copy = [...fields];
	if (sortBy === 'confidence-asc') {
		return copy.sort((a, b) => (a.confidence ?? 100) - (b.confidence ?? 100));
	}
	if (sortBy === 'confidence-desc') {
		return copy.sort((a, b) => (b.confidence ?? 0) - (a.confidence ?? 0));
	}
	return copy;
};

export const groupFieldsBySection = (fields) => {
	const groups = new Map();
	for (const field of fields) {
		const sectionName = field?.section || 'Autres';
		if (!groups.has(sectionName)) {
			groups.set(sectionName, []);
		}
		groups.get(sectionName).push(field);
	}
	return Array.from(groups.entries());
};

/**
 * @param {object[]} fields
 * @param {{ showOnlyNeedsCorrection?: boolean, sortBy?: string, excludeSections?: Set<string> }} opts
 */
export const buildGroupedFilteredFields = (
	fields,
	{ showOnlyNeedsCorrection = false, sortBy = 'section', excludeSections = new Set() } = {}
) => {
	let list = fields.filter((f) => !excludeSections.has(f?.section || ''));
	if (showOnlyNeedsCorrection) {
		list = list.filter(fieldNeedsCorrection);
	}
	list = sortValidationFields(list, sortBy);
	return groupFieldsBySection(list);
};
