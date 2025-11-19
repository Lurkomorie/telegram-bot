import { Navigate, Route, BrowserRouter as Router, Routes } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Statistics from './components/Statistics';
import Users from './components/Users';
import UserTimeline from './components/UserTimeline';
import AcquisitionSources from './components/AcquisitionSources';
import StartCodes from './components/StartCodes';
import Images from './components/Images';
import PremiumStatistics from './components/PremiumStatistics';
import ReferralStats from './components/ReferralStats';
import AuthGuard from './components/AuthGuard';
import Characters from './components/Characters';
import Translations from './components/Translations';

function App() {
  return (
    <Router basename="/analytics">
      <Routes>
        {/* Referral route without auth - public */}
        <Route path="/referral/:sourceName" element={<ReferralStats />} />
        
        {/* Main routes with sidebar and auth */}
        <Route path="/*" element={
          <AuthGuard>
            <div className="flex h-screen bg-gray-100">
              <Sidebar />
              <main className="flex-1 overflow-auto">
                <Routes>
                  <Route path="/" element={<Navigate to="/statistics" replace />} />
                  <Route path="/statistics" element={<Statistics />} />
                  <Route path="/users" element={<Users />} />
                  <Route path="/users/:clientId" element={<UserTimeline />} />
                  <Route path="/acquisition-sources" element={<AcquisitionSources />} />
                  <Route path="/start-codes" element={<StartCodes />} />
                  <Route path="/characters" element={<Characters />} />
                  <Route path="/images" element={<Images />} />
                  <Route path="/premium-statistics" element={<PremiumStatistics />} />
                  <Route path="/translations" element={<Translations />} />
                </Routes>
              </main>
            </div>
          </AuthGuard>
        } />
      </Routes>
    </Router>
  );
}

export default App;
