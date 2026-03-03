import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Switch } from '@/components/ui/Switch';
import { Button } from '@/components/ui/Button';
import { Shield, AlertTriangle, Clock, Gavel } from 'lucide-react';

export function Moderation() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-display font-bold text-gray-900 tracking-tight">Moderation System</h1>
        <p className="text-gray-500 mt-2 text-lg">Configure warning thresholds, auto-punishments, and escalation rules.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2.5 bg-indigo-50 text-indigo-600 rounded-xl">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <CardTitle>Warning System</CardTitle>
            </div>
            <CardDescription>Configure how warnings are handled and when they expire.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between p-4 bg-cream-50 rounded-2xl border border-cream-200">
              <div>
                <h4 className="font-semibold text-gray-900">Enable Warnings</h4>
                <p className="text-sm text-gray-500">Allow moderators to issue formal warnings.</p>
              </div>
              <Switch checked={true} />
            </div>
            
            <div className="space-y-3">
              <label className="text-sm font-medium text-gray-700">Warning Expiration</label>
              <select className="w-full bg-cream-50 border border-cream-300 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all">
                <option>Never</option>
                <option>30 Days</option>
                <option>60 Days</option>
                <option>90 Days</option>
              </select>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2.5 bg-red-50 text-red-600 rounded-xl">
                <Gavel className="w-5 h-5" />
              </div>
              <CardTitle>Auto-Punishments</CardTitle>
            </div>
            <CardDescription>Automatically punish users who accumulate too many warnings.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {[
              { warns: 3, action: 'Timeout for 1 Hour' },
              { warns: 5, action: 'Kick from Server' },
              { warns: 7, action: 'Ban permanently' },
            ].map((rule, i) => (
              <div key={i} className="flex items-center gap-4 p-4 bg-cream-50 rounded-2xl border border-cream-200">
                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-white border border-cream-300 font-bold text-gray-700">
                  {rule.warns}
                </div>
                <div className="text-sm font-medium text-gray-600">Warnings =</div>
                <div className="flex-1 bg-white border border-cream-300 rounded-xl px-4 py-2 text-sm font-semibold text-gray-900">
                  {rule.action}
                </div>
                <Button variant="ghost" size="sm" className="text-red-500 hover:text-red-600 hover:bg-red-50">
                  Remove
                </Button>
              </div>
            ))}
            <Button variant="outline" className="w-full border-dashed border-2 border-cream-300 text-gray-500 hover:text-indigo-600 hover:border-indigo-300 hover:bg-indigo-50">
              + Add Escalation Rule
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
