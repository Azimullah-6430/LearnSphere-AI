import React, { useState, useEffect } from 'react';
import Header from '../../components/Header';
import Sidebar from '../../components/Sidebar';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { analyticsService } from '../../services/apiService';
import toast from 'react-hot-toast';

const StudentAnalytics: React.FC = () => {
  const [performanceData, setPerformanceData] = useState<any>(null);
  const [chartData, setChartData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const performance = await analyticsService.getStudentPerformance();
        setPerformanceData(performance);

        const chart = await analyticsService.getProgressChart();
        setChartData(chart.progress_data || []);
      } catch (error) {
        toast.error('Failed to load analytics');
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
  }, []);

  if (loading) {
    return (
      <div className="flex h-screen bg-gray-100">
        <Sidebar />
        <div className="flex-1 flex flex-col">
          <Header />
          <main className="flex-1 flex items-center justify-center">
            <div className="text-2xl font-bold text-gray-600">Loading analytics...</div>
          </main>
        </div>
      </div>
    );
  }

  const subjectData = performanceData?.subject_averages ? Object.entries(performanceData.subject_averages).map(([subject, data]: any) => ({
    subject: subject.charAt(0).toUpperCase() + subject.slice(1),
    average: data.average,
  })) : [];

  return (
    <div className="flex h-screen bg-gray-100">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header />
        <main className="flex-1 overflow-auto p-8">
          <div className="max-w-7xl mx-auto">
            <h1 className="text-3xl font-bold mb-8">📊 Your Performance Analytics</h1>

            {/* Key Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
              <div className="bg-white rounded-lg shadow p-6 text-center">
                <p className="text-gray-600 text-sm">Overall Average</p>
                <p className="text-3xl font-bold text-blue-600 mt-2">
                  {performanceData?.average_score?.toFixed(1)}%
                </p>
              </div>
              <div className="bg-white rounded-lg shadow p-6 text-center">
                <p className="text-gray-600 text-sm">Total Evaluations</p>
                <p className="text-3xl font-bold text-green-600 mt-2">
                  {performanceData?.total_evaluations}
                </p>
              </div>
              <div className="bg-white rounded-lg shadow p-6 text-center">
                <p className="text-gray-600 text-sm">Focus Hours This Month</p>
                <p className="text-3xl font-bold text-orange-600 mt-2">
                  {(performanceData?.focus_time_this_month_minutes / 60).toFixed(1)}h
                </p>
              </div>
              <div className="bg-white rounded-lg shadow p-6 text-center">
                <p className="text-gray-600 text-sm">Encouragement Tokens</p>
                <p className="text-3xl font-bold text-purple-600 mt-2">
                  {performanceData?.encouragement_tokens}
                </p>
              </div>
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
              {/* Progress Trend */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold mb-4">Progress Trend</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="score" stroke="#3B82F6" strokeWidth={2} name="Score %" />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Subject Performance */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold mb-4">Subject-wise Average</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={subjectData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="subject" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="average" fill="#10B981" name="Average %" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Additional Metrics */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">Study Statistics</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <p className="text-gray-600 text-sm">Average Focus Score</p>
                  <p className="text-2xl font-bold text-blue-600 mt-2">
                    {performanceData?.average_focus_score?.toFixed(1) || '0'}/100
                  </p>
                </div>
                <div className="bg-green-50 p-4 rounded-lg">
                  <p className="text-gray-600 text-sm">Total Study Time</p>
                  <p className="text-2xl font-bold text-green-600 mt-2">
                    {(performanceData?.focus_time_this_month_minutes / 60).toFixed(1)}h
                  </p>
                </div>
                <div className="bg-purple-50 p-4 rounded-lg">
                  <p className="text-gray-600 text-sm">Best Performance</p>
                  <p className="text-2xl font-bold text-purple-600 mt-2">
                    {Math.max(...(performanceData?.scores_trend || [0])).toFixed(1)}%
                  </p>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default StudentAnalytics;