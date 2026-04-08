import { Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import Navbar from './Navbar';
import SideNav from './SideNav';

function MainLayout() {
	const { isAuthenticated } = useAuth();
	const location = useLocation();

	const appPaths = ['/dashboard', '/import', '/history'];
	const showSideNav =
		isAuthenticated && appPaths.some((path) => location.pathname === path || location.pathname.startsWith(`${path}/`));

	return (
		<div className={`main-layout ${showSideNav ? 'with-sidebar' : ''}`}>
			{showSideNav ? <SideNav /> : <Navbar />}
			<main className={`main-content ${showSideNav ? 'with-sidebar' : ''}`}>
				<Outlet />
			</main>
		</div>
	);
}

export default MainLayout;
