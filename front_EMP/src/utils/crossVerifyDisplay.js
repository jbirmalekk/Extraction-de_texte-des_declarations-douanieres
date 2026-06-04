const trim = (value) => String(value ?? '').trim();

/** Libellé source / partenaire : numéro + date (DUM ou facture). */
export function buildRegisteredDocLine(type, numero, date, fallbackId) {
	const isDum = type === 'dum';
	const numKey = isDum ? 'N° déclaration' : 'N° facture';
	const dateKey = isDum ? 'Date déclaration' : 'Date facture';
	const n = trim(numero);
	const d = trim(date);
	if (n && d) {
		return `${numKey} ${n} · ${dateKey} ${d}`;
	}
	if (n) {
		return `${numKey} ${n}`;
	}
	if (d) {
		return `${dateKey} ${d}`;
	}
	return isDum ? `DUM #${fallbackId}` : `Facture #${fallbackId}`;
}

/** Suffixe facture déjà liée à une DUM (numéro + date, pas l’id technique). */
export function buildLinkedDumSuffix(dumDoc, numeroDeclarationDum) {
	const n = trim(dumDoc?.numero_declaration) || trim(numeroDeclarationDum);
	const d = trim(dumDoc?.date_declaration);
	if (n && d) {
		return `liée DUM n° ${n} · ${d}`;
	}
	if (n) {
		return `liée DUM n° ${n}`;
	}
	return '';
}

export function resolveSourceRegisteredLine({
	sourceType,
	sourceId,
	session,
	dumDocs,
	invoices,
}) {
	const id = Number(sourceId);
	if (!Number.isFinite(id) || id <= 0) {
		return '—';
	}

	if (sourceType === 'dum') {
		const doc = dumDocs.find((d) => d.id === id);
		const numero =
			doc?.numero_declaration || session?.sourceNumero || session?.sourceLabel;
		const date = doc?.date_declaration || session?.sourceDate;
		return buildRegisteredDocLine('dum', numero, date, id);
	}

	if (sourceType === 'invoice') {
		const inv = invoices.find((i) => i.id === id);
		const numero =
			inv?.numero_facture || session?.sourceNumero || session?.sourceLabel;
		const date = inv?.date_facture || session?.sourceDate;
		return buildRegisteredDocLine('invoice', numero, date, id);
	}

	return '—';
}

export function indexDumDocsById(dumDocs) {
	const map = new Map();
	for (const doc of dumDocs || []) {
		if (doc?.id != null) {
			map.set(Number(doc.id), doc);
		}
	}
	return map;
}
