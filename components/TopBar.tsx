import Image from 'next/image'
import Link from 'next/link'
import styles from '../styles/TopBar.module.css'
import swarmLogo from "../public/SwarmLogo.svg"

export default function TopBar() {
  return (
    <div className={styles.topBar}>
      <div className={styles.leftContent}>
        <Link href="/">
          <a>
            <Image src={swarmLogo} alt="Swarm Logo" width={32} height={32} />
          </a>
        </Link>
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
