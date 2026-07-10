import { Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '@/shared/hooks/useAuth';
import Navbar from '@/shared/components/layout/Navbar';
import SideNav from '@/shared/components/layout/SideNav';
import { ExtractionJobsProvider } from '@/shared/store/ExtractionJobsContext';

function MainLayout() {
	const { isAuthenticated } = useAuth();
	const location = useLocation();

	const appPaths = [
		'/dashboard',
		'/admin/dashboard',
		'/documents',
		'/invoices',
		'/import',
		'/ocr-result',
		'/invoice-ocr-result',
		'/batch-results',
		'/validation',
		'/invoice-validation',
		'/cross-verification',
		'/reports',
		'/erp-success',
		'/history',
		'/profile',
		'/admin',
	];
	const showSideNav =
		isAuthenticated && appPaths.some((path) => location.pathname === path || location.pathname.startsWith(`${path}/`));

	return (
		<ExtractionJobsProvider>
			<div className={`main-layout ${showSideNav ? 'with-sidebar' : ''}`}>
				{showSideNav ? <SideNav /> : <Navbar />}
				<main className={`main-content ${showSideNav ? 'with-sidebar' : ''}`}>
					<Outlet />
				</main>
			</div>
		</ExtractionJobsProvider>
	);
}

export default MainLayout;
