import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './components/AppLayout.jsx'
import RouteLoader from './components/RouteLoader.jsx'
import Login from './pages/Login.jsx'

const Dashboard = lazy(() => import('./pages/Dashboard.jsx'))
const Evaluate = lazy(() => import('./pages/Evaluate.jsx'))
const History = lazy(() => import('./pages/History.jsx'))
const Plagiarism = lazy(() => import('./pages/Plagiarism.jsx'))
const Analytics = lazy(() => import('./pages/Analytics.jsx'))
const Reports = lazy(() => import('./pages/Reports.jsx'))
const Students = lazy(() => import('./pages/Students.jsx'))
const Performance = lazy(() => import('./pages/Performance.jsx'))
const Trainer = lazy(() => import('./pages/Trainer.jsx'))
const Parent = lazy(() => import('./pages/Parent.jsx'))
const Focus = lazy(() => import('./pages/Focus.jsx'))
const Memory = lazy(() => import('./pages/Memory.jsx'))
const SelfEvaluation = lazy(() => import('./pages/SelfEvaluation.jsx'))
const Notifications = lazy(() => import('./pages/Notifications.jsx'))
const Settings = lazy(() => import('./pages/Settings.jsx'))
const NotFound = lazy(() => import('./pages/NotFound.jsx'))
const KnowledgeChallenge = lazy(() => import('./pages/KnowledgeChallenge.jsx'))
const MisconceptionMap = lazy(() => import('./pages/MisconceptionMap.jsx'))
const ActionCenter = lazy(() => import('./pages/ActionCenter.jsx'))
const RealityLab = lazy(() => import('./pages/RealityLab.jsx'))
const CurrentOpportunities = lazy(() => import('./pages/CurrentOpportunities.jsx'))
const CreateClassPage = lazy(() => import('./pages/CreateClassPage.jsx'))
const SelectClass = lazy(() => import('./pages/SelectClass.jsx'))
const LearnAnywhere = lazy(() => import('./pages/LearnAnywhere.jsx'))

function Lazy({ children }) {
  return <Suspense fallback={<RouteLoader />}>{children}</Suspense>
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Login />} />
      <Route path="/create-class" element={<Lazy><CreateClassPage /></Lazy>} />
      <Route path="/app" element={<AppLayout />}>
        <Route path="select-class" element={<Lazy><SelectClass /></Lazy>} />
        <Route path="dashboard" element={<Lazy><Dashboard /></Lazy>} />
        <Route path="evaluate" element={<Lazy><Evaluate /></Lazy>} />
        <Route path="history" element={<Lazy><History /></Lazy>} />
        <Route path="plagiarism" element={<Lazy><Plagiarism /></Lazy>} />
        <Route path="analytics" element={<Lazy><Analytics /></Lazy>} />
        <Route path="reports" element={<Lazy><Reports /></Lazy>} />
        <Route path="students" element={<Lazy><Students /></Lazy>} />
        <Route path="performance" element={<Lazy><Performance /></Lazy>} />
        <Route path="trainer" element={<Lazy><Trainer /></Lazy>} />
        <Route path="parent" element={<Lazy><Parent /></Lazy>} />
        <Route path="focus" element={<Lazy><Focus /></Lazy>} />
        <Route path="memory" element={<Lazy><Memory /></Lazy>} />
        <Route path="self-evaluation" element={<Lazy><SelfEvaluation /></Lazy>} />
        <Route path="notifications" element={<Lazy><Notifications /></Lazy>} />
        <Route path="settings" element={<Lazy><Settings /></Lazy>} />
        <Route path="knowledge-challenge" element={<Lazy><KnowledgeChallenge /></Lazy>} />
        <Route path="misconception-map" element={<Lazy><MisconceptionMap /></Lazy>} />
        <Route path="action-center" element={<Lazy><ActionCenter /></Lazy>} />
        <Route path="reality-lab" element={<Lazy><RealityLab /></Lazy>} />
        <Route path="opportunities" element={<Lazy><CurrentOpportunities /></Lazy>} />
        <Route path="learn-anywhere" element={<Lazy><LearnAnywhere /></Lazy>} />
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="*" element={<Lazy><NotFound /></Lazy>} />
      </Route>
      <Route path="*" element={<Lazy><NotFound /></Lazy>} />
    </Routes>
  )
}
