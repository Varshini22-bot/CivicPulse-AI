import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { LandingPage } from '../pages/LandingPage';
import { api } from '../services/api';

vi.mock('../services/api', () => ({
  api: {
    getKPIs: vi.fn().mockResolvedValue({
      total_reports: 120,
      resolved_reports: 80,
      active_hotspots: 4,
      avg_resolution_time_days: 3.2
    }),
    trackReportByNumber: vi.fn().mockImplementation((num: string) => {
      if (num === 'CP-2026-0001') {
        return Promise.resolve({ id: 'rep-uuid-1', tracking_number: 'CP-2026-0001' });
      }
      return Promise.reject(new Error('Tracking number not found'));
    })
  }
}));

describe('LandingPage Public Tracking', () => {
  it('renders public tracking input and navigates on success', async () => {
    const onNavigate = vi.fn();
    render(<LandingPage onNavigate={onNavigate} />);

    const input = screen.getByPlaceholderText(/Enter Tracking Number/i);
    expect(input).toBeInTheDocument();

    fireEvent.change(input, { target: { value: 'CP-2026-0001' } });
    const trackBtn = screen.getByRole('button', { name: /Track Status/i });
    fireEvent.click(trackBtn);

    await waitFor(() => {
      expect(onNavigate).toHaveBeenCalledWith('issue-details', { reportId: 'rep-uuid-1' });
    });
  });

  it('displays error message when tracking number is invalid', async () => {
    const onNavigate = vi.fn();
    render(<LandingPage onNavigate={onNavigate} />);

    const input = screen.getByPlaceholderText(/Enter Tracking Number/i);
    fireEvent.change(input, { target: { value: 'CP-INVALID-999' } });
    const trackBtn = screen.getByRole('button', { name: /Track Status/i });
    fireEvent.click(trackBtn);

    await waitFor(() => {
      expect(screen.getByText(/Tracking number not found/i)).toBeInTheDocument();
    });
  });
});
