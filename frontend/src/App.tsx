import { Routes, Route } from "react-router-dom";
import { ProtectedRoute } from "@/features/auth/protected-route";
import { LoginPage } from "@/features/auth/login-page";
import { AppLayout } from "@/components/layout/app-layout";
import { DashboardPage } from "@/features/dashboard/dashboard-page";
import { AccountsListPage } from "@/features/accounts/accounts-list-page";
import { AccountDetailPage } from "@/features/accounts/account-detail-page";
import { ContactsListPage } from "@/features/contacts/contacts-list-page";
import { ContactDetailPage } from "@/features/contacts/contact-detail-page";
import { OpportunitiesListPage } from "@/features/opportunities/opportunities-list-page";
import { OpportunityDetailPage } from "@/features/opportunities/opportunity-detail-page";
import { LeadsListPage } from "@/features/leads/leads-list-page";
import { LeadDetailPage } from "@/features/leads/lead-detail-page";
import { CasesListPage } from "@/features/cases/cases-list-page";
import { CaseDetailPage } from "@/features/cases/case-detail-page";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="accounts" element={<AccountsListPage />} />
          <Route path="accounts/:id" element={<AccountDetailPage />} />
          <Route path="contacts" element={<ContactsListPage />} />
          <Route path="contacts/:id" element={<ContactDetailPage />} />
          <Route path="opportunities" element={<OpportunitiesListPage />} />
          <Route path="opportunities/:id" element={<OpportunityDetailPage />} />
          <Route path="leads" element={<LeadsListPage />} />
          <Route path="leads/:id" element={<LeadDetailPage />} />
          <Route path="cases" element={<CasesListPage />} />
          <Route path="cases/:id" element={<CaseDetailPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
