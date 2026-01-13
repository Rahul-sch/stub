import { AlertCircle, Info, Lightbulb, AlertTriangle } from 'lucide-react';
import { ReactNode } from 'react';

type CalloutType = 'eli5' | 'warning' | 'info' | 'tip';

interface CalloutBlockProps {
  type: CalloutType;
  title?: string;
  children: ReactNode;
}

const calloutConfig: Record<
  CalloutType,
  {
    icon: React.ComponentType<{ className?: string }>;
    bgColor: string;
    borderColor: string;
    iconColor: string;
    defaultTitle: string;
  }
> = {
  eli5: {
    icon: Lightbulb,
    bgColor: 'bg-[var(--accent-purple)]/10',
    borderColor: 'border-[var(--accent-purple)]',
    iconColor: 'text-[var(--accent-purple)]',
    defaultTitle: 'Explain Like I\'m 5',
  },
  warning: {
    icon: AlertTriangle,
    bgColor: 'bg-[var(--accent-orange)]/10',
    borderColor: 'border-[var(--accent-orange)]',
    iconColor: 'text-[var(--accent-orange)]',
    defaultTitle: 'Warning',
  },
  info: {
    icon: Info,
    bgColor: 'bg-[var(--accent-cyan)]/10',
    borderColor: 'border-[var(--accent-cyan)]',
    iconColor: 'text-[var(--accent-cyan)]',
    defaultTitle: 'Info',
  },
  tip: {
    icon: AlertCircle,
    bgColor: 'bg-[var(--accent-green)]/10',
    borderColor: 'border-[var(--accent-green)]',
    iconColor: 'text-[var(--accent-green)]',
    defaultTitle: 'Pro Tip',
  },
};

export function CalloutBlock({ type, title, children }: CalloutBlockProps) {
  const config = calloutConfig[type];
  const Icon = config.icon;
  const displayTitle = title || config.defaultTitle;

  return (
    <div
      className={`my-6 rounded-lg border-l-4 ${config.borderColor} ${config.bgColor} p-4`}
    >
      <div className="flex items-start gap-3">
        <Icon className={`w-5 h-5 mt-0.5 shrink-0 ${config.iconColor}`} />
        <div className="flex-1">
          <div className={`font-semibold mb-2 ${config.iconColor}`}>
            {displayTitle}
          </div>
          <div className="text-[var(--foreground-muted)] leading-relaxed">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
