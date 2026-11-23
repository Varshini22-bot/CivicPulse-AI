import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatusBadge, PriorityBadge, CategoryBadge } from '../components/ui/Badge';

describe('UI Badges', () => {
  it('renders StatusBadge correctly with proper styling', () => {
    render(<StatusBadge status="Under Review" />);
    const badge = screen.getByText('Under Review');
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain('bg-purple-50');
  });

  it('renders PriorityBadge correctly with critical priority', () => {
    render(<PriorityBadge level="Critical" score={89} />);
    expect(screen.getByText(/Critical/i)).toBeInTheDocument();
    expect(screen.getByText('(89)')).toBeInTheDocument();
  });

  it('renders CategoryBadge with category name', () => {
    render(<CategoryBadge category="Potholes & Road Damage" />);
    expect(screen.getByText('Potholes & Road Damage')).toBeInTheDocument();
  });
});
