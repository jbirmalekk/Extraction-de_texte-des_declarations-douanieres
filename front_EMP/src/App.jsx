
import './App.css';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import ProtectedRoute from '@/features/auth/components/ProtectedRoute';
import MainLayout from '@/shared/components/layout/MainLayout';
import WelcomePage from '@/features/home/pages/WelcomePage';
import LoginPage from '@/features/auth/pages/LoginPage';
import RegisterPage from '@/features/auth/pages/RegisterPage';
import ForgotPasswordPage from '@/features/auth/pages/ForgotPasswordPage';
import ResetPasswordPage from '@/features/auth/pages/ResetPasswordPage';
import VerifyEmailPage from '@/features/auth/pages/VerifyEmailPage';
import ImportPage from '@/features/import/pages/ImportPage';
import NotFoundPage from '@/features/home/pages/NotFoundPage';
import DashboardPage from '@/features/dashboard/pages/DashboardPage';
import HistoryPage from '@/features/history/pages/HistoryPage';
import ProfilePage from '@/features/auth/pages/ProfilePage';
import AdminUsersPage from '@/features/admin/pages/AdminUsersPage';
import AdminDashboardPage from '@/features/dashboard/pages/AdminDashboardPage';
import DocumentDetailPage from '@/features/detail/pages/DocumentDetailPage';
import InvoiceDetailPage from '@/features/detail/pages/InvoiceDetailPage';
import OcrResultPage from '@/features/extraction/pages/OcrResultPage';
import InvoiceOcrResultPage from '@/features/extraction/pages/InvoiceOcrResultPage';
import BatchResultsPage from '@/features/extraction/pages/BatchResultsPage';
import ValidationPage from '@/features/validation/pages/ValidationPage';
import InvoiceValidationPage from '@/features/validation/pages/InvoiceValidationPage';
import CrossVerificationPage from '@/features/reconciliation/pages/CrossVerificationPage';
import ErpSuccessPage from '@/features/erp/pages/ErpSuccessPage';
import ReportsPage from '@/features/reports/pages/ReportsPage';
import ReportDetailPage from '@/features/reports/pages/ReportDetailPage';

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

