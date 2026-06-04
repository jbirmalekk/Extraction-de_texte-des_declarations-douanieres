import { test, expect } from '@playwright/test';

/**
 * Smoke : pages critiques accessibles (sans auth complète si route protégée → redirection login).
 */
test.describe('Parcours EMP — pages workflow', () => {
	test('page login affiche le formulaire', async ({ page }) => {
		await page.goto('/login');
		await expect(page.getByRole('heading', { name: /connexion/i })).toBeVisible({
			timeout: 15_000,
		});
	});

	test('routes validation et réconciliation répondent', async ({ page }) => {
		await page.goto('/validation');
		const validationBody = await page.locator('body').innerText();
		expect(
			validationBody.includes('Validation') ||
				validationBody.includes('connexion') ||
				validationBody.includes('login')
		).toBeTruthy();

		await page.goto('/cross-verification');
		const crossBody = await page.locator('body').innerText();
		expect(
			crossBody.includes('Réconciliation') ||
				crossBody.includes('conformité') ||
				crossBody.includes('connexion')
		).toBeTruthy();
	});
});
