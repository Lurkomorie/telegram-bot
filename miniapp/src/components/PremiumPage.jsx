import { useState } from 'react';
import './PremiumPage.css';

/**
 * PremiumPage Component
 * Shows energy packages and pricing for users to purchase more energy
 */
export default function PremiumPage({ energy, onBack }) {
  const [selectedPackage, setSelectedPackage] = useState(null);

  const packages = [
    {
      id: 'starter',
      name: 'Starter Pack',
      energy: 50,
      price: 100, // Telegram Stars
      popular: false,
    },
    {
      id: 'popular',
      name: 'Popular Pack',
      energy: 150,
      price: 250,
      popular: true,
      discount: '15% OFF',
    },
    {
      id: 'premium',
      name: 'Premium Pack',
      energy: 500,
      price: 750,
      popular: false,
      discount: '25% OFF',
    },
  ];

  const handlePurchase = (pkg) => {
    setSelectedPackage(pkg);
    // TODO: Implement Telegram Stars payment
    // For now, just show alert
    alert(`Purchase ${pkg.name} for ${pkg.price} Stars - Coming soon!`);
  };

  return (
    <div className="premium-page">
      <div className="energy-status-card">
        <div className="energy-icon">⚡</div>
        <div className="energy-info">
          <div className="energy-label">Your Energy</div>
          <div className="energy-amount">{energy.energy} / {energy.max_energy}</div>
        </div>
      </div>

      <div className="packages-section">
        <h3>Energy Packages</h3>
        <div className="packages-grid">
          {packages.map((pkg) => (
            <PackageCard
              key={pkg.id}
              package={pkg}
              onPurchase={() => handlePurchase(pkg)}
            />
          ))}
        </div>
      </div>

      <div className="footer-note">
        <p>💫 Payments are processed securely through Telegram</p>
      </div>
    </div>
  );
}

function PackageCard({ package: pkg, onPurchase }) {
  return (
    <div className={`package-card ${pkg.popular ? 'popular' : ''}`}>
      {pkg.popular && <div className="popular-badge">MOST POPULAR</div>}
      {pkg.discount && <div className="discount-badge">{pkg.discount}</div>}
      
      <div className="package-icon">⚡</div>
      <h4 className="package-name">{pkg.name}</h4>
      <div className="package-energy">+{pkg.energy} Energy</div>
      <div className="package-price">{pkg.price} ⭐</div>
      
      <button className="purchase-button" onClick={onPurchase}>
        Purchase
      </button>
    </div>
  );
}

