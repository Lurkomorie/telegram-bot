import { Navigate, Route, BrowserRouter as Router, Routes } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Statistics from './components/Statistics';
import Users from './components/Users';
import UserTimeline from './components/UserTimeline';
import AcquisitionSources from './components/AcquisitionSources';
import Images from './components/Images';
import SystemMessages from './components/SystemMessages';
import SystemMessageTemplates from './components/SystemMessageTemplates';

function App() {
  return (
    <Router basename="/analytics">
      <div className="flex h-screen bg-gray-100">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<Navigate to="/statistics" replace />} />
            <Route path="/statistics" element={<Statistics />} />
            <Route path="/users" element={<Users />} />
            <Route path="/users/:clientId" element={<UserTimeline />} />
            <Route path="/acquisition-sources" element={<AcquisitionSources />} />
            <Route path="/images" element={<Images />} />
            <Route path="/system-messages" element={<SystemMessages />} />
            <Route path="/system-messages/templates" element={<SystemMessageTemplates />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
