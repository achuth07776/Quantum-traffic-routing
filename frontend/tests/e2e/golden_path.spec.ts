import { test, expect } from '@playwright/test';

test.describe('Visakhapatnam Traffic & Fleet Platform — Golden Path E2E Suite', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveTitle(/Visakhapatnam/i);
  });

  test('Flow 1: Driver Mode — Real-World Road Route Calculation (RK Beach -> Rushikonda)', async ({ page }) => {
    const driverTab = page.locator('nav[aria-label="Product Modes"]').getByRole('button', { name: /Driver/i });
    await expect(driverTab).toBeVisible();

    // Toggle to landmark presets mode (default is search mode)
    const presetToggle = page.getByTitle('Switch to landmark presets');
    await expect(presetToggle).toBeVisible({ timeout: 5000 });
    await presetToggle.click();

    const originSelect = page.locator('select[aria-label="Origin Landmark"]');
    await expect(originSelect).toBeVisible({ timeout: 5000 });

    const calcBtn = page.getByRole('button', { name: /Calculate Real-World Road Route/i });
    await expect(calcBtn).toBeVisible();
    await calcBtn.click();

    // Verify authoritative Trip Summary metrics render exactly from backend
    await expect(page.getByText(/Trip Summary/i)).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/10\.57 km|10\.6 km/i).first()).toBeVisible();
    await expect(page.getByText(/10\.9 min/i).first()).toBeVisible();
    await expect(page.getByText(/Turn-by-Turn Route/i)).toBeVisible();

    // Verify SVG polyline drawn on Leaflet map canvas
    const leafletPaths = page.locator('.leaflet-pane svg path');
    await expect(leafletPaths.first()).toBeVisible({ timeout: 10000 });
  });

  test('Flow 2: Driver Mode — Location Review Warning for Off-Road Landmark (Kailasagiri)', async ({ page }) => {
    // Toggle to landmark presets mode
    const presetToggle = page.getByTitle('Switch to landmark presets');
    await expect(presetToggle).toBeVisible({ timeout: 5000 });
    await presetToggle.click();

    const destSelect = page.locator('select[aria-label="Destination Landmark"]');
    await expect(destSelect).toBeVisible({ timeout: 5000 });
    await destSelect.selectOption('kailasagiri_hill');

    await expect(page.getByText(/Location needs confirmation/i)).toBeVisible({ timeout: 5000 });
    await expect(page.getByRole('button', { name: /REVIEW LOCATION/i })).toBeVisible();
  });

  test('Flow 3: Driver Mode — Traffic Provenance & Disambiguation Badges', async ({ page }) => {
    await expect(page.locator('text=/OSRM · Road Routing/i').first()).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=/TRAFFIC/i').first()).toBeVisible();
  });

  test('Flow 4: Fleet Mode — Dynamic Traffic Shock Reoptimization & Changed Metrics', async ({ page }) => {
    const fleetTab = page.locator('nav[aria-label="Product Modes"]').getByRole('button', { name: /Fleet/i });
    await expect(fleetTab).toBeVisible();
    await fleetTab.click();

    await expect(page.getByText(/Central Fleet Depot/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/Customer Delivery Stops/i)).toBeVisible();

    // Trigger controlled corridor shock
    const shockBtn = page.getByRole('button', { name: /Beach Rd Shock/i });
    await expect(shockBtn).toBeVisible();
    await shockBtn.click();

    // Validate changed metrics render: inaction penalty vs reoptimized schedule & delay avoided
    await expect(page.getByText(/TRAFFIC SHOCK DETECTED/i)).toBeVisible({ timeout: 20000 });
    await expect(page.getByText(/Previous plan under current traffic/i)).toBeVisible();
    await expect(page.getByText(/Reoptimized plan/i)).toBeVisible();
    await expect(page.getByText(/Congestion Delay Avoided/i)).toBeVisible();
    await expect(page.getByText(/Decision Trade-Off/i)).toBeVisible();
  });

  test('Flow 5: Fleet Mode — Vehicle Tours and Operational Schedule Display', async ({ page }) => {
    const fleetTab = page.locator('nav[aria-label="Product Modes"]').getByRole('button', { name: /Fleet/i });
    await fleetTab.click();

    await expect(page.getByRole('button', { name: /Dispatch Fleet/i })).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/Customer Delivery Stops/i)).toBeVisible();
  });

  test('Flow 6: Offline & Air-Gap Demo Cache Indicator Verification', async ({ page }) => {
    const header = page.locator('header');
    await expect(header.getByText('TRAFFIC', { exact: true })).toBeVisible({ timeout: 5000 });
    await expect(header.getByText('ROUTING', { exact: true })).toBeVisible();
  });

  test('Flow 7: Scientific Validation Tab — Benchmarks & Provenance Audit', async ({ page }) => {
    const benchTab = page.locator('nav[aria-label="Product Modes"]').getByRole('button', { name: /Research/i });
    await expect(benchTab).toBeVisible();
    await benchTab.click();

    await expect(page.locator('h1, h2, h3').filter({ hasText: /Validation|Benchmark|Scientific|Research/i }).first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/OR-Tools/i).first()).toBeVisible();
    await expect(page.getByText(/QPSO/i).first()).toBeVisible();
    await expect(page.getByText(/Exact Validation/i).first()).toBeVisible();
  });

  test('Flow 8: Quantum Lab — Verification of Mandatory Research Disclaimer & Simulation', async ({ page }) => {
    const quantumTab = page.locator('nav[aria-label="Product Modes"]').getByRole('button', { name: /Quantum/i });
    await expect(quantumTab).toBeVisible();
    await quantumTab.click();

    await expect(
      page.locator('text=/RESEARCH SIMULATION — NOT USED FOR LIVE ROUTE SELECTION/i').first()
    ).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/4-Qubit QUBO/i)).toBeVisible({ timeout: 15000 });
  });

  test('Flow 9: Global Reset Demo Action restores initial clean baseline state', async ({ page }) => {
    // 1. First mutate state by calculating a route
    const calcBtn = page.getByRole('button', { name: /Calculate Real-World Road Route/i });
    if (await calcBtn.isVisible()) {
      await calcBtn.click();
      await expect(page.getByText(/Trip Summary/i)).toBeVisible({ timeout: 15000 });
    }

    // 2. Trigger Global Reset Demo
    const resetBtn = page.getByRole('button', { name: /Reset Demo/i });
    await expect(resetBtn).toBeVisible();
    await resetBtn.click();

    // 3. Verify actual baseline state restored
    await expect(page.getByRole('button', { name: /Calculate Real-World Road Route/i })).toBeVisible({ timeout: 10000 });
  });

});
