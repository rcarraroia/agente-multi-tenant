// Compatibility layer for legacy toast usage
export { useToast, type Toast, type ToastFunction } from "@/components/ui/toast"

// Legacy toast function for direct usage
import { useToast as useToastHook } from "@/components/ui/toast"

export const toast = {
  success: (title: string, description?: string) => {
    // This is a fallback - components should use useToast hook
    console.log('Toast Success:', title, description);
  },
  error: (title: string, description?: string) => {
    console.log('Toast Error:', title, description);
  }
};

// Hook for components that need the toast function
export const useToastFunction = () => {
  const { toast } = useToastHook();
  return { toast };
};
