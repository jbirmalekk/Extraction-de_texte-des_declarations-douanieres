const PASSWORD_POLICY_MESSAGE_EN =
	'Password must contain at least 8 characters, including uppercase, lowercase, number, and special character.';

const PASSWORD_POLICY_MESSAGE_FR =
	'Le mot de passe doit contenir au moins 8 caracteres, avec majuscule, minuscule, chiffre et caractere special.';

const PASSWORD_NO_SPACES_EN = 'Password must not contain spaces.';
const PASSWORD_NO_SPACES_FR = 'Le mot de passe ne doit pas contenir d espace.';

export const getPasswordPolicyMessage = (locale = 'en') =>
	locale === 'fr' ? PASSWORD_POLICY_MESSAGE_FR : PASSWORD_POLICY_MESSAGE_EN;

export const validatePasswordPolicy = (password, locale = 'en') => {
	const message = getPasswordPolicyMessage(locale);
	const noSpacesMessage = locale === 'fr' ? PASSWORD_NO_SPACES_FR : PASSWORD_NO_SPACES_EN;

	if (typeof password !== 'string') {
		return { isValid: false, message };
	}

	if (/\s/.test(password)) {
		return { isValid: false, message: noSpacesMessage };
	}

	const isValid =
		password.length >= 8 &&
		/[a-z]/.test(password) &&
		/[A-Z]/.test(password) &&
		/\d/.test(password) &&
		/[^A-Za-z0-9]/.test(password);

	return {
		isValid,
		message: isValid ? '' : message,
	};
};
