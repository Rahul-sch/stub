'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { BookOpen, Code2, Map, HelpCircle, Home, Zap } from 'lucide-react';
import clsx from 'clsx';

const navItems = [
  { href: '/', label: 'Home', icon: Home },
  { href: '/wiki', label: 'Wiki', icon: BookOpen },
  { href: '/xray', label: 'Code X-Ray', icon: Code2 },
  { href: '/map', label: 'System Map', icon: Map },
  { href: '/faq', label: 'Warlord FAQ', icon: HelpCircle },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="flex items-center gap-2 mb-8 px-2">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[var(--accent-cyan)] to-[var(--accent-purple)] flex items-center justify-center">
          <Zap className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-gradient">Ithena</h1>
          <p className="text-xs text-[var(--foreground-muted)]">The Blueprint</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            item.href === '/'
              ? pathname === '/'
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx('sidebar-nav-item', isActive && 'active')}
            >
              <Icon className="w-5 h-5" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="absolute bottom-6 left-6 right-6">
        <div className="text-xs text-[var(--foreground-muted)] space-y-1">
          <p>Rig Alpha Learning OS</p>
          <p className="opacity-60">v1.0.0</p>
        </div>
      </div>
    </aside>
  );
}
