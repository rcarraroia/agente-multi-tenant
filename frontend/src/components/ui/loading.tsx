/**
 * Componentes de Loading States melhorados.
 * 
 * Fornece diferentes tipos de loading para melhor UX:
 * - Spinner simples
 * - Skeleton loading
 * - Loading com mensagem
 * - Loading de página completa
 */

import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ 
  size = 'md', 
  className = '' 
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8'
  };

  return (
    <Loader2 className={`animate-spin ${sizeClasses[size]} ${className}`} />
  );
};

interface LoadingMessageProps {
  message: string;
  submessage?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const LoadingMessage: React.FC<LoadingMessageProps> = ({ 
  message, 
  submessage,
  size = 'md' 
}) => {
  return (
    <div className="flex flex-col items-center justify-center space-y-3 p-6">
      <LoadingSpinner size={size} className="text-blue-600" />
      <div className="text-center">
        <p className="text-gray-900 font-medium">{message}</p>
        {submessage && (
          <p className="text-gray-600 text-sm mt-1">{submessage}</p>
        )}
      </div>
    </div>
  );
};

interface FullPageLoadingProps {
  message?: string;
  submessage?: string;
}

export const FullPageLoading: React.FC<FullPageLoadingProps> = ({ 
  message = 'Carregando...', 
  submessage 
}) => {
  return (
    <div className="fixed inset-0 bg-white bg-opacity-90 flex items-center justify-center z-50">
      <LoadingMessage message={message} submessage={submessage} size="lg" />
    </div>
  );
};

interface SkeletonProps {
  className?: string;
  lines?: number;
}

export const Skeleton: React.FC<SkeletonProps> = ({ className = '', lines = 1 }) => {
  return (
    <div className={`animate-pulse ${className}`}>
      {Array.from({ length: lines }).map((_, index) => (
        <div
          key={index}
          className={`bg-gray-200 rounded ${
            index === lines - 1 ? 'w-3/4' : 'w-full'
          } h-4 ${index > 0 ? 'mt-2' : ''}`}
        />
      ))}
    </div>
  );
};

interface CardSkeletonProps {
  showAvatar?: boolean;
  lines?: number;
}

export const CardSkeleton: React.FC<CardSkeletonProps> = ({ 
  showAvatar = false, 
  lines = 3 
}) => {
  return (
    <div className="animate-pulse p-4 border rounded-lg">
      <div className="flex items-start space-x-3">
        {showAvatar && (
          <div className="w-10 h-10 bg-gray-200 rounded-full flex-shrink-0" />
        )}
        <div className="flex-1 space-y-2">
          <div className="h-4 bg-gray-200 rounded w-1/4" />
          {Array.from({ length: lines }).map((_, index) => (
            <div
              key={index}
              className={`h-3 bg-gray-200 rounded ${
                index === lines - 1 ? 'w-3/4' : 'w-full'
              }`}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

interface TableSkeletonProps {
  rows?: number;
  columns?: number;
}

export const TableSkeleton: React.FC<TableSkeletonProps> = ({ 
  rows = 5, 
  columns = 4 
}) => {
  return (
    <div className="animate-pulse">
      {/* Header */}
      <div className="flex space-x-4 p-4 border-b">
        {Array.from({ length: columns }).map((_, index) => (
          <div key={index} className="h-4 bg-gray-200 rounded flex-1" />
        ))}
      </div>
      
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="flex space-x-4 p-4 border-b">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <div 
              key={colIndex} 
              className={`h-3 bg-gray-200 rounded flex-1 ${
                colIndex === 0 ? 'w-1/4' : colIndex === columns - 1 ? 'w-1/6' : ''
              }`} 
            />
          ))}
        </div>
      ))}
    </div>
  );
};

interface ButtonLoadingProps {
  loading: boolean;
  children: React.ReactNode;
  disabled?: boolean;
  className?: string;
  onClick?: () => void;
  type?: 'button' | 'submit' | 'reset';
}

export const ButtonLoading: React.FC<ButtonLoadingProps> = ({
  loading,
  children,
  disabled,
  className = '',
  onClick,
  type = 'button'
}) => {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={loading || disabled}
      className={`
        relative inline-flex items-center justify-center
        px-4 py-2 border border-transparent text-sm font-medium rounded-md
        text-white bg-blue-600 hover:bg-blue-700
        focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
        disabled:opacity-50 disabled:cursor-not-allowed
        transition-colors duration-200
        ${className}
      `}
    >
      {loading && (
        <LoadingSpinner size="sm" className="mr-2" />
      )}
      {children}
    </button>
  );
};

// Hook para gerenciar estados de loading
export const useLoading = (initialState = false) => {
  const [loading, setLoading] = React.useState(initialState);

  const withLoading = React.useCallback(async <T,>(
    asyncOperation: () => Promise<T>
  ): Promise<T> => {
    setLoading(true);
    try {
      const result = await asyncOperation();
      return result;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    loading,
    setLoading,
    withLoading
  };
};

export default {
  LoadingSpinner,
  LoadingMessage,
  FullPageLoading,
  Skeleton,
  CardSkeleton,
  TableSkeleton,
  ButtonLoading,
  useLoading
};