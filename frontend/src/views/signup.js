import React from "react";
import NavBar from "../components/NavBar";
import Footer from "../components/Footer";
import { Box } from "@chakra-ui/react";
import SignUpForm from "../components/SignUpForm";

const signup = () => (
  <Box id="signUpPage" backgroundImage="background.png">
    <NavBar />
    <SignUpForm title="Sign Up" />
    <Footer />
  </Box>
);

export default signup;
