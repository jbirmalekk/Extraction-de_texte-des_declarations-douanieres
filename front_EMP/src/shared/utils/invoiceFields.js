/**
 * Mappe la réponse API facture vers les champs du formulaire.
 * Par défaut : uniquement les champs extraits (valeur non vide), hors contrôle DUM vide.
 */

const hasValue = (v) => v != null && String(v).trim() !== '';

/** Champs du tableau totaux facture EMP — toujours affichés si l'un est rempli. */
const MONTANTS_KEYS = new Set([
	'montant_brut',
	'montant_remise',
	'montant_ht_ou_amount',
	'montant_ttc',
	'net_pay',
]);

const formatAmount = (v) => {
	if (v == null || v === '') {
		return '';
	}
	const n = Number(v);
	if (Number.isFinite(n)) {
		return Number.isInteger(n) ? String(n) : String(n);
	}
	return String(v);
};

/**
 * @param {Record<string, unknown>} inv
 * @param {{ onlyPopulated?: boolean, includeControleDum?: boolean }} [options]
 */
export const mapInvoiceBackendToFields = (inv, options = {}) => {
	const { onlyPopulated = true, includeControleDum = false } = options;

	if (!inv || typeof inv !== 'object') {
		return [];
	}

	const fc = inv.field_confidence && typeof inv.field_confidence === 'object' ? inv.field_confidence : {};

	const scalar = (key, label, section, formatter = (v) => (v == null || v === '' ? '' : String(v))) => {
		const raw = inv[key];
		const value = formatter(raw);
		const c = fc[key];
		const conf = typeof c === 'number' ? Math.round(Math.min(1, Math.max(0, c)) * 100) : null;
		return {
			id: key,
			key,
			label,
			section,
			value,
			confidence: conf,
			hasError: false,
			isManual: false,
		};
	};

	const rows = [
		scalar('numero_facture', 'Numero facture', 'Identification'),
		scalar('date_facture', 'Date facture', 'Identification'),
		scalar('devise', 'Devise', 'Identification'),
		scalar('notes_reference', 'Notes / references', 'Identification'),
		scalar('client_code', 'Code client', 'Client'),
		scalar('client_nom', 'Nom client', 'Client'),
		scalar('client_pays', 'Pays client', 'Client'),
		scalar('client_matricule_fiscal', 'Matricule fiscal / Tax ID', 'Client'),
		scalar('adresse_facturation', 'Adresse facturation', 'Client', (v) => (v == null ? '' : String(v))),
		scalar('adresse_expedition', 'Adresse expedition', 'Client', (v) => (v == null ? '' : String(v))),
		scalar('adresse_livraison', 'Adresse livraison', 'Client', (v) => (v == null ? '' : String(v))),
		scalar('montant_brut', 'Montant brut (Gross)', 'Montants', formatAmount),
		scalar('montant_remise', 'Remise (Discount)', 'Montants', formatAmount),
		scalar('montant_ht_ou_amount', 'Montant / Amount', 'Montants', formatAmount),
		scalar('montant_ttc', 'TTC / All taxes included', 'Montants', formatAmount),
		scalar('net_pay', 'NET PAY', 'Montants', formatAmount),
		scalar('nombre_colis', 'Nombre de colis', 'Logistique', (v) => (v == null ? '' : String(v))),
		scalar('poids_brut_kg', 'Poids brut (kg)', 'Logistique', formatAmount),
		scalar('poids_net_kg', 'Poids net (kg)', 'Logistique', formatAmount),
		scalar('incoterm', 'Incoterm', 'Conditions'),
		scalar('mode_transport_libelle', 'Mode transport', 'Conditions'),
		scalar('conditions_paiement', 'Conditions de paiement', 'Conditions'),
	];

	if (includeControleDum) {
		rows.push(
			scalar('numero_declaration_dum', 'N° declaration DUM', 'Controle DUM'),
			scalar('montant_declare_dum', 'PFN article DUM', 'Controle DUM', formatAmount),
			scalar('devise_declaree_dum', 'Devise DUM', 'Controle DUM'),
			scalar('ecart_montant', 'Ecart (facture - DUM PFN)', 'Controle DUM', formatAmount),
			scalar('ecart_commentaire', 'Commentaire controle', 'Controle DUM'),
			scalar('statut_controle', 'Statut controle', 'Controle DUM')
		);
	}

	const lineFieldDefs = [
		{ sub: 'reference', label: 'Reference' },
		{ sub: 'designation', label: 'Designation' },
		{ sub: 'quantite', label: 'Quantite', fmt: formatAmount },
		{ sub: 'prix_unitaire', label: 'Prix unitaire', fmt: formatAmount },
		{ sub: 'montant_ligne', label: 'Montant', fmt: formatAmount },
		{ sub: 'devise_ligne', label: 'Devise' },
	];

	const lines = Array.isArray(inv.lines) ? inv.lines : [];
	lines.forEach((line, idx) => {
		const order = line.line_order ?? idx;
		const lineNum = order + 1;
		lineFieldDefs.forEach(({ sub, label, fmt }) => {
			const raw = line[sub];
			const value = (fmt || ((v) => (v == null ? '' : String(v))))(raw);
			rows.push({
				id: `line_${order}_${sub}`,
				key: `line_${order}_${sub}`,
				label: `Ligne ${lineNum} — ${label}`,
				section: 'Lignes facture',
				value,
				confidence: typeof fc.lines === 'number' ? Math.round(fc.lines * 100) : null,
				hasError: false,
				isManual: false,
			});
		});
	});

	if (!onlyPopulated) {
		return rows;
	}

	const hasLineAmounts = lines.some(
		(l) => l.montant_ligne != null && Number(l.montant_ligne) > 0
	);
	const montantsPopulated =
		rows.some((f) => MONTANTS_KEYS.has(f.key) && hasValue(f.value)) || hasLineAmounts;

	return rows.filter((field) => {
		if (field.section === 'Controle DUM') {
			return hasValue(field.value);
		}
		if (MONTANTS_KEYS.has(field.key) && montantsPopulated) {
			return true;
		}
		return hasValue(field.value);
	});
};

/** Après comparaison DUM : réinjecte les champs de contrôle remplis. */
export const mergeControleDumFields = (fields, inv) => {
	const base = mapInvoiceBackendToFields(inv, {
		onlyPopulated: true,
		includeControleDum: true,
	});
	const controle = base.filter((f) => f.section === 'Controle DUM' && hasValue(f.value));
	const rest = fields.filter((f) => f.section !== 'Controle DUM');
	return [...rest, ...controle];
};

const LINE_KEY = /^line_(\d+)_(reference|designation|quantite|prix_unitaire|montant_ligne|devise_ligne)$/;

/**
 * Construit le corps PATCH à partir des champs du formulaire.
 * @param {Array<{ id: string, value: string }>} fields
 */
export const buildInvoicePatchFromFields = (fields) => {
	const patch = {};
	const lineMap = new Map();

	for (const f of fields) {
		const id = f.id || '';
		const val = f.value == null ? '' : String(f.value).trim();
		const m = id.match(LINE_KEY);
		if (m) {
			const order = Number(m[1]);
			const sub = m[2];
			if (!lineMap.has(order)) {
				lineMap.set(order, { line_order: order });
			}
			const row = lineMap.get(order);
			if (sub === 'quantite' || sub === 'prix_unitaire' || sub === 'montant_ligne') {
				const num = val === '' ? null : Number(val.replace(',', '.'));
				row[sub] = Number.isFinite(num) ? num : null;
			} else {
				row[sub] = val === '' ? null : val;
			}
			continue;
		}

		const scalarKeys = new Set([
			'numero_facture',
			'date_facture',
			'devise',
			'notes_reference',
			'client_code',
			'client_nom',
			'client_pays',
			'client_matricule_fiscal',
			'adresse_facturation',
			'adresse_expedition',
			'adresse_livraison',
			'montant_brut',
			'montant_remise',
			'montant_ht_ou_amount',
			'montant_ttc',
			'net_pay',
			'nombre_colis',
			'poids_brut_kg',
			'poids_net_kg',
			'incoterm',
			'mode_transport_libelle',
			'conditions_paiement',
		]);
		if (scalarKeys.has(id)) {
			if (
				[
					'montant_brut',
					'montant_remise',
					'montant_ht_ou_amount',
					'montant_ttc',
					'net_pay',
					'poids_brut_kg',
					'poids_net_kg',
				].includes(id)
			) {
				patch[id] = val === '' ? null : Number(val.replace(',', '.'));
				if (patch[id] !== null && !Number.isFinite(patch[id])) {
					patch[id] = null;
				}
			} else if (id === 'nombre_colis') {
				patch[id] = val === '' ? null : parseInt(val, 10);
				if (patch[id] !== null && !Number.isFinite(patch[id])) {
					patch[id] = null;
				}
			} else {
				patch[id] = val === '' ? null : val;
			}
		}
	}

	const lines = [...lineMap.entries()]
		.sort((a, b) => a[0] - b[0])
		.map(([, row]) => row);
	if (lines.length > 0) {
		patch.lines = lines;
	}

	return patch;
};

export const DEFAULT_INVOICE_BADGE = 'FACTURE';
