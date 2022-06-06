import { useSession } from "next-auth/react"

export default function Account() {

    const { data: session, status } = useSession()

    if (!session) {
        return <p>You are not logged in</p>
    }

    return (
        <div>
            <h1>Account</h1>
            <p>
                This is the account page for {session?.user?.name}
            </p>
        </div>
    )
}