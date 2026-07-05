import { useGame } from './state/gameStore'
import { StartPage } from './pages/StartPage'
import { GamePage } from './pages/GamePage'
import { MeetingPage } from './pages/MeetingPage'
import { ResultPage } from './pages/ResultPage'

export default function App() {
  const screen = useGame((s) => s.screen)
  return (
    <>
      <div className="relative z-10">
        {screen === 'start' && <StartPage />}
        {screen === 'game' && <GamePage />}
        {screen === 'meeting' && <MeetingPage />}
        {screen === 'result' && <ResultPage />}
      </div>
      <div className="crt-vignette" />
      <div className="scanlines" />
    </>
  )
}
