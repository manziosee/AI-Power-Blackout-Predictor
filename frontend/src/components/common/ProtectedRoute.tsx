import { Navigate } from "react-router-dom";
import { useUserStore } from "../../store/user";

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useUserStore((s) => s.token);
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
