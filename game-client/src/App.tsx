import { useGame } from './state/gameStore'
import { StartPage } from './pages/StartPage'
import { GamePage } from './pages/GamePage'
import { SolvePage } from './pages/SolvePage'
import { ResultPage } from './pages/ResultPage'

export default function App() {
  const screen = useGame((s) => s.screen)
  return (
    <>
      <div className="sparkle" />
      <div className="relative z-10">
        {screen === 'start' && <StartPage />}
        {screen === 'game' && <GamePage />}
        {screen === 'solve' && <SolvePage />}
        {screen === 'result' && <ResultPage />}
      </div>
    </>
  )
}
