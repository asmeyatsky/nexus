import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Building2,
  Users,
  TrendingUp,
  UserPlus,
  Headphones,
  BarChart3,
  LineChart,
  Wand2,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/accounts", label: "Accounts", icon: Building2 },
  { to: "/contacts", label: "Contacts", icon: Users },
  { to: "/opportunities", label: "Opportunities", icon: TrendingUp },
  { to: "/leads", label: "Leads", icon: UserPlus },
  { to: "/cases", label: "Cases", icon: Headphones },
  { to: "/reports", label: "Reports", icon: BarChart3 },
  { to: "/analytics", label: "Analytics", icon: LineChart },
  { to: "/report-builder", label: "Report Builder", icon: Wand2 },
];

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex h-14 items-center border-b px-4">
        <span className="text-lg font-semibold">Nexus CRM</span>
      </div>
      <nav className="flex-1 space-y-1 p-2">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )
            }
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
