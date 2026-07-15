
import './App.css';
import { lazy, Suspense } from 'react';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import ProtectedRoute from '@/features/auth/components/ProtectedRoute';
import MainLayout from '@/shared/components/layout/MainLayout';

const WelcomePage = lazy(() => import('@/features/home/pages/WelcomePage'));
const LoginPage = lazy(() => import('@/features/auth/pages/LoginPage'));
const RegisterPage = lazy(() => import('@/features/auth/pages/RegisterPage'));
const ForgotPasswordPage = lazy(() => import('@/features/auth/pages/ForgotPasswordPage'));
const ResetPasswordPage = lazy(() => import('@/features/auth/pages/ResetPasswordPage'));
const VerifyEmailPage = lazy(() => import('@/features/auth/pages/VerifyEmailPage'));
const ImportPage = lazy(() => import('@/features/import/pages/ImportPage'));
const NotFoundPage = lazy(() => import('@/features/home/pages/NotFoundPage'));
const DashboardPage = lazy(() => import('@/features/dashboard/pages/DashboardPage'));
const HistoryPage = lazy(() => import('@/features/history/pages/HistoryPage'));
const ProfilePage = lazy(() => import('@/features/auth/pages/ProfilePage'));
const AdminUsersPage = lazy(() => import('@/features/admin/pages/AdminUsersPage'));
const AdminDashboardPage = lazy(() => import('@/features/dashboard/pages/AdminDashboardPage'));
const DocumentDetailPage = lazy(() => import('@/features/detail/pages/DocumentDetailPage'));
const InvoiceDetailPage = lazy(() => import('@/features/detail/pages/InvoiceDetailPage'));
const OcrResultPage = lazy(() => import('@/features/extraction/pages/OcrResultPage'));
const InvoiceOcrResultPage = lazy(() => import('@/features/extraction/pages/InvoiceOcrResultPage'));
const BatchResultsPage = lazy(() => import('@/features/extraction/pages/BatchResultsPage'));
const ValidationPage = lazy(() => import('@/features/validation/pages/ValidationPage'));
const InvoiceValidationPage = lazy(() => import('@/features/validation/pages/InvoiceValidationPage'));
const CrossVerificationPage = lazy(() => import('@/features/reconciliation/pages/CrossVerificationPage'));
const ErpSuccessPage = lazy(() => import('@/features/erp/pages/ErpSuccessPage'));
const ReportsPage = lazy(() => import('@/features/reports/pages/ReportsPage'));
const ReportDetailPage = lazy(() => import('@/features/reports/pages/ReportDetailPage'));

const RouteFallback = () => (
  <div className="app-route-loading" role="status">
    Chargement...
  </div>
);

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
  return (
    <Suspense fallback={<RouteFallback />}>
      <RouterProvider router={router} />
    </Suspense>
  );
}

export default App;
