import Image from 'next/image'
import Link from 'next/link'
import styles from '../styles/TopBar.module.css'
import swarmLogo from "../public/SwarmLogo.svg"
import { GetServerSidePropsContext } from 'next'
import { signOut, useSession } from "next-auth/react"

export default function TopBar() {

  const { data: session, status } = useSession()

  let signUpContent = null

  if (session) {
    signUpContent = (
      <button onClick={() => signOut()}>
        <a>Log out</a>
      </button>
    )
  }
  else {
    signUpContent = (
      <Link href="/api/auth/signin">
        Log in
      </Link>
    )
  }

  let contentIfLoggedIn = null

  if (session) {
    contentIfLoggedIn = (
      <Link href="/account">
        Account
      </Link>
    )
  }

  return (
    <div className={styles.topBar}>
      <div className={styles.leftContent}>
        <Link href="/">
          <a>
            <Image src={swarmLogo} alt="Swarm Logo" width={32} height={32} />
          </a>
        </Link>
        <Link href="/projects">
          Projects
        </Link>
        {contentIfLoggedIn}
      </div>
      <div className={styles.rightContent}>
        {signUpContent}
      </div>
    </div>
  )
}