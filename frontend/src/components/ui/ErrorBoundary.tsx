import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from './Button';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('CivicPulse Uncaught Client Error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-[50vh] flex flex-col items-center justify-center p-6 text-center space-y-4">
          <div className="p-3 bg-red-100 dark:bg-red-950/50 text-red-600 rounded-full">
            <AlertCircle className="w-8 h-8" />
          </div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">Something went wrong</h2>
          <p className="text-xs text-slate-500 max-w-md">
            An unexpected error occurred in this view. Your session data is intact.
          </p>
          <div className="p-2.5 bg-slate-100 dark:bg-slate-800 rounded-lg text-xs font-mono text-slate-700 dark:text-slate-300 max-w-lg truncate">
            {this.state.error?.message}
          </div>
          <Button
            variant="primary"
            onClick={() => window.location.reload()}
            icon={<RefreshCw className="w-4 h-4" />}
          >
            Reload Platform
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
