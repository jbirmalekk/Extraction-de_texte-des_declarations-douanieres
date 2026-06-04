
import './App.css';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import ProtectedRoute from './components/Auth/ProtectedRoute';
import MainLayout from './components/Layout/MainLayout';
import WelcomePage from './pages/WelcomePage';
import LoginPage from './pages/auth/LoginPage';
import RegisterPage from './pages/auth/RegisterPage';
import ForgotPasswordPage from './pages/auth/ForgotPasswordPage';
import ResetPasswordPage from './pages/auth/ResetPasswordPage';
import VerifyEmailPage from './pages/VerifyEmailPage';
import ImportPage from './pages/ImportPage';
import NotFoundPage from './pages/NotFoundPage';
import DashboardPage from './pages/DashboardPage';
import HistoryPage from './pages/HistoryPage';
import ProfilePage from './pages/ProfilePage';
import AdminUsersPage from './pages/AdminUsersPage';
import AdminDashboardPage from './pages/AdminDashboardPage';
import DocumentDetailPage from './pages/DocumentDetailPage';
import InvoiceDetailPage from './pages/InvoiceDetailPage';
import OcrResultPage from './pages/OcrResultPage';
import InvoiceOcrResultPage from './pages/InvoiceOcrResultPage';
import BatchResultsPage from './pages/BatchResultsPage';
import ValidationPage from './pages/ValidationPage';
import InvoiceValidationPage from './pages/InvoiceValidationPage';
import CrossVerificationPage from './pages/CrossVerificationPage';
import ErpSuccessPage from './pages/ErpSuccessPage';
import ReportsPage from './pages/ReportsPage';
import ReportDetailPage from './pages/ReportDetailPage';

const router = createBrowserRouter([
  {
    path: '/',
    element: <MainLayout />,
    children: [
      {
        index: true,
        element: <WelcomePage />,
      },
      {
        path: 'dashboard',
        element: (
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'admin/dashboard',
        element: (
          <ProtectedRoute allowedRoles={['admin']}>
            <AdminDashboardPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'documents/:documentId',
        element: (
          <ProtectedRoute>
            <DocumentDetailPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'invoices/:invoiceId',
        element: (
          <ProtectedRoute>
            <InvoiceDetailPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'import',
        element: (
          <ProtectedRoute>
            <ImportPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'ocr-result',
        element: (
          <ProtectedRoute>
            <OcrResultPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'invoice-ocr-result',
        element: (
          <ProtectedRoute>
            <InvoiceOcrResultPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'batch-results',
        element: (
          <ProtectedRoute>
            <BatchResultsPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'validation',
        element: (
          <ProtectedRoute>
            <ValidationPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'invoice-validation',
        element: (
          <ProtectedRoute>
            <InvoiceValidationPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'cross-verification',
        element: (
          <ProtectedRoute>
            <CrossVerificationPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'erp-success',
        element: (
          <ProtectedRoute>
            <ErpSuccessPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'reports',
        element: (
          <ProtectedRoute>
            <ReportsPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'reports/:invoiceId',
        element: (
          <ProtectedRoute>
            <ReportDetailPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'history',
        element: (
          <ProtectedRoute>
            <HistoryPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'profile',
        element: (
          <ProtectedRoute>
            <ProfilePage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'admin/users',
        element: (
          <ProtectedRoute allowedRoles={['admin']}>
            <AdminUsersPage />
          </ProtectedRoute>
        ),
      },
    ],
  },
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/forgot-password',
    element: <ForgotPasswordPage />,
  },
  {
    path: '/reset-password',
    element: <ResetPasswordPage />,
  },
  {
    path: '/register',
    element: <RegisterPage />,
  },
  {
    path: '/verify-email',
    element: <VerifyEmailPage />,
  },
  {
    path: '*',
    element: <NotFoundPage />,
  },
]);

function App() {
  return <RouterProvider router={router} />;
}

export default App;

