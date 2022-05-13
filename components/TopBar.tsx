import Link from 'next/link'
import styles from '../styles/TopBar.module.css'

export default function TopBar() {
  return (
    <div className={styles.topBar}>
      <div className={styles.leftContent}>
        <Link href="/">Swarm</Link>
      </div>
      <div className={styles.rightContent}>
        <ul>
          <li>
            <button type="submit">Sign in</button>
          </li>
        </ul>
      </div>
    </div>
  )
}
